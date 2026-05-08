# Acceleration and Backend Specification

## 1. Goal

Provide one processing interface with multiple implementations:

1. CPU baseline for correctness and universal support.
2. CUDA acceleration for Windows machines with compatible NVIDIA GPUs.
3. MPS/Metal acceleration for macOS Apple Silicon where operations are supported.
4. Operation-level fallback when a backend lacks an operation.

## 2. Backend Types

| Backend | Platform | Implementation |
|---|---|---|
| `cpu` | macOS + Windows | NumPy + OpenCV |
| `torch_cuda` | Windows + NVIDIA | PyTorch tensors on `cuda` |
| `torch_mps` | macOS Apple Silicon | PyTorch tensors on `mps` |
| `opencv_cuda` | Windows + NVIDIA | OpenCV CUDA module, optional custom build |

## 3. Backend Selection

### Auto Selection Algorithm

```python
def select_backend(preference: str, platform: str) -> Backend:
    if preference == "cpu":
        return CpuBackend()

    if preference == "cuda" and TorchCudaBackend.is_available():
        return TorchCudaBackend()

    if preference == "mps" and TorchMpsBackend.is_available():
        return TorchMpsBackend()

    if preference == "opencv_cuda" and OpenCvCudaBackend.is_available():
        return OpenCvCudaBackend()

    if preference == "auto":
        if platform == "win32" and TorchCudaBackend.is_available():
            return TorchCudaBackend()
        if platform == "win32" and OpenCvCudaBackend.is_available():
            return OpenCvCudaBackend()
        if platform == "darwin" and TorchMpsBackend.is_available():
            return TorchMpsBackend()

    return CpuBackend()
```

## 4. Runtime Probes

### CUDA Probe

```python
def has_torch_cuda():
    import torch
    return torch.cuda.is_available()
```

### MPS Probe

```python
def has_torch_mps():
    import torch
    return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
```

### OpenCV CUDA Probe

```python
def has_opencv_cuda():
    import cv2
    return hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0
```

## 5. Operation Contract

Each operation declares backend support.

| Operation | CPU | Torch CUDA | Torch MPS | OpenCV CUDA |
|---|---|---|---|---|
| remap / warp | Yes | Target | Target when supported | Target |
| gaussian blur | Yes | Target | Target | Target |
| bilateral-like smoothing | Yes | Approximate | Approximate | Optional |
| alpha blend | Yes | Yes | Yes | Yes |
| Lab color conversion | Yes | Optional | Optional | CPU fallback |
| mask creation | Yes | Optional | Optional | CPU fallback |
| landmark detection | CPU | Optional future | Optional future | CPU |

## 6. Torch Backend Design

### Tensor Layout

Use `NCHW` float32 tensors.

```text
NumPy RGB HWC float32 0..1
  ↓
Torch NCHW float32 on device
  ↓
Processing
  ↓
NumPy RGB HWC float32 0..1
```

### Warp with Grid Sampling

```python
def torch_remap(image_np, grid_np, device):
    # image_np: HWC RGB float32 0..1
    # grid_np: HWC2 normalized sampling grid [-1, 1]
    img = torch.from_numpy(image_np).permute(2, 0, 1).unsqueeze(0).to(device)
    grid = torch.from_numpy(grid_np).unsqueeze(0).to(device)
    out = torch.nn.functional.grid_sample(
        img,
        grid,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )
    return out.squeeze(0).permute(1, 2, 0).cpu().numpy()
```

### Gaussian Blur

Use separable convolution with generated Gaussian kernel.

```python
def gaussian_blur_torch(img, sigma):
    # Create 1D Gaussian kernel and apply horizontal + vertical conv.
    pass
```

### MPS Fallback Policy

Some PyTorch operations may be unsupported on MPS in specific versions. Wrap each operation:

```python
try:
    return mps_operation(...)
except Exception as exc:
    log.warn("MPS operation fallback to CPU", exc_info=exc)
    return cpu_operation(...)
```

## 7. OpenCV CUDA Backend Design

OpenCV CUDA can accelerate remap and filtering when the app bundles a CUDA-enabled OpenCV build.

### Remap

```python
def opencv_cuda_remap(image, map_x, map_y):
    gpu_image = cv2.cuda_GpuMat()
    gpu_image.upload(image)
    gpu_map_x = cv2.cuda_GpuMat()
    gpu_map_y = cv2.cuda_GpuMat()
    gpu_map_x.upload(map_x.astype(np.float32))
    gpu_map_y.upload(map_y.astype(np.float32))
    gpu_out = cv2.cuda.remap(gpu_image, gpu_map_x, gpu_map_y, interpolation=cv2.INTER_LINEAR)
    return gpu_out.download()
```

### Packaging Caveat

The default `opencv-python` pip wheels are CPU-focused. CUDA usage usually requires custom OpenCV build or separate distribution strategy. V1 should treat OpenCV CUDA as optional.

## 8. CPU Backend Design

CPU backend implements all operations through NumPy/OpenCV.

### Remap

```python
result = cv2.remap(
    image,
    map_x.astype(np.float32),
    map_y.astype(np.float32),
    interpolation=cv2.INTER_LINEAR,
    borderMode=cv2.BORDER_REFLECT_101,
)
```

### Blur

```python
result = cv2.GaussianBlur(image, ksize=(0, 0), sigmaX=sigma, sigmaY=sigma)
```

### Bilateral

```python
result = cv2.bilateralFilter(image, d=diameter, sigmaColor=sigma_color, sigmaSpace=sigma_space)
```

## 9. Backend Fallback Rules

1. Engine chooses active backend at startup.
2. Each operation asks backend for implementation.
3. When operation is unsupported, use CPU implementation.
4. Log fallback once per operation type per session.
5. UI status can show `Backend: MPS + CPU fallback`.

## 10. Performance Strategy

### Preview

- Use downscaled preview.
- Keep image on GPU across sequential operations when using torch backend.
- Avoid CPU/GPU round trips inside one pipeline.
- Cache masks and landmarks.

### Export

- Use original image.
- Use tiled processing for very large images if memory pressure occurs.
- Use progress events per stage.

## 11. Memory Management

### GPU Memory

- Reuse tensors where possible.
- Explicitly release references after export.
- For CUDA, optionally call `torch.cuda.empty_cache()` after large exports.
- For MPS, rely on Python object lifetime and test memory release behavior.

### CPU Memory

- Avoid duplicate full-resolution copies.
- Convert to float32 only once per pipeline.
- Use preview cache for UI.

## 12. Device Diagnostics

Engine should expose diagnostics:

```json
{
  "active_backend": "torch_cuda",
  "fallbacks": ["lab_color_conversion:cpu"],
  "torch": {
    "cuda_available": true,
    "mps_available": false,
    "device_name": "NVIDIA ..."
  },
  "opencv": {
    "cuda_device_count": 1
  }
}
```

## 13. Implementation Priority

1. CPU backend with correct results.
2. Torch backend for remap and simple filters.
3. MPS/CUDA runtime selection.
4. OpenCV CUDA optional path.
5. Native CUDA/Metal kernels after UX and quality are stable.

## 14. Native Metal Future Path

A future native Metal backend can be added as a separate module:

```text
python engine
  ↓
ctypes/cffi/native extension
  ↓
Metal compute shader
  ↓
remap/filter kernels
```

The V1 design keeps backend abstraction stable so native Metal can replace torch MPS for image operations later.

## 15. Native CUDA Future Path

A future native CUDA backend can implement:

- Dense warp map generation.
- Remap.
- Gaussian blur.
- Mask feathering.
- Alpha blending.

Expose it through a Python extension and implement the same `ImageBackend` contract.

