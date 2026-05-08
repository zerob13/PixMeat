# Technical Specification

## 1. Stack Summary

| Layer | Technology |
|---|---|
| Desktop framework | Electron |
| Renderer UI | React + TypeScript + Vite |
| Styling | CSS Modules or Tailwind CSS |
| State management | Zustand or Redux Toolkit |
| Canvas | HTML Canvas 2D first, WebGL optional later |
| Main process | TypeScript |
| Local engine | Python 3.11/3.12 |
| Image arrays | NumPy |
| Image IO | Pillow + imageio + OpenCV |
| CV operations | OpenCV |
| Face landmarks | MediaPipe Face Landmarker / Face Mesh |
| Tensor acceleration | PyTorch |
| Optional inference runtime | ONNX Runtime |
| Packaging | electron-builder + bundled Python executable |

## 2. Runtime Strategy

### Electron Runtime

Electron provides the app shell, menus, file dialogs, and UI rendering. The renderer never performs heavy image processing.

### Python Runtime

Python contains the processing engine because its ecosystem is stronger for:

- OpenCV image processing.
- MediaPipe face landmarks.
- PyTorch CUDA/MPS tensor operations.
- Rapid algorithm iteration.
- Golden-image testing.

## 3. Acceleration Strategy

### V1 Backends

| Backend | Platform | Purpose |
|---|---|---|
| CPU OpenCV/NumPy | macOS + Windows | Baseline and fallback |
| Torch CUDA | Windows + NVIDIA | Warp, filtering, tensor color ops |
| Torch MPS | macOS Apple Silicon | Warp, filtering, tensor color ops where supported |
| OpenCV CUDA | Windows + NVIDIA | Optional remap/filter acceleration when custom OpenCV build is available |

### Backend Priority

```text
Auto backend:
  Windows:
    1. Torch CUDA
    2. OpenCV CUDA
    3. CPU

  macOS:
    1. Torch MPS
    2. CPU
```

### Backend Contract

Every backend implements this interface:

```python
class ImageBackend:
    name: str
    device: str

    def is_available(self) -> bool: ...
    def remap(self, image, map_x, map_y, interpolation: str): ...
    def gaussian_blur(self, image, sigma: float): ...
    def bilateral_like_filter(self, image, radius: int, sigma_color: float, sigma_space: float): ...
    def alpha_blend(self, base, overlay, mask): ...
    def color_adjust_lab(self, image, mask, params): ...
```

Backends may implement a subset. Missing operations fall back per operation.

## 4. Image Representation

### Internal Format

Use RGB float32 arrays in range `0.0-1.0` for core processing.

```text
Input JPEG/PNG/TIFF
  ↓
Decode
  ↓
RGB or RGBA uint8/uint16
  ↓
Convert to RGB float32 0..1
  ↓
Process
  ↓
Convert to output format
```

### Alpha Handling

- If input has alpha, preserve alpha during export where output supports alpha.
- Core face retouching operates on RGB channels.
- Alpha channel is carried through as a separate plane.

### Color Management

V1 uses basic sRGB assumptions. Future RAW/color-managed workflow adds ICC profile support.

## 5. File IO

### Decode Priority

1. Pillow for common formats.
2. imageio fallback for WebP/TIFF variants.
3. OpenCV fallback for readable formats.

### Encode Priority

1. Pillow for JPEG/PNG/TIFF.
2. OpenCV fallback for JPEG/PNG.

### Metadata

V1 optionally copies basic EXIF metadata for JPEG where Pillow supports it. Export remains valid when metadata copy fails.

## 6. Parameter Schema

Parameter values are normalized in UI and engine.

```python
@dataclass
class LiquifyParams:
    face_slim: float = 0.0      # 0..1
    jawline: float = 0.0        # 0..1
    chin_length: float = 0.0    # -1..1
    eye_enlarge: float = 0.0    # 0..1
    nose_slim: float = 0.0      # 0..1
    smile: float = 0.0          # 0..1

@dataclass
class SkinParams:
    skin_smooth: float = 0.0    # 0..1
    texture_keep: float = 0.7   # 0..1
    blemish_soften: float = 0.0 # 0..1
    skin_tone_even: float = 0.0 # 0..1

@dataclass
class BeautyParams:
    brightness: float = 0.0     # -1..1
    eye_bright: float = 0.0     # 0..1
    teeth_white: float = 0.0    # 0..1
    soft_contrast: float = 0.0  # -1..1
```

UI displays human-friendly ranges and converts to normalized engine values.

## 7. TypeScript Parameter Types

```ts
export type LiquifyParams = {
  faceSlim: number;      // 0..100
  jawline: number;       // 0..100
  chinLength: number;    // -50..50
  eyeEnlarge: number;    // 0..100
  noseSlim: number;      // 0..100
  smile: number;         // 0..100
};

export type SkinParams = {
  skinSmooth: number;    // 0..100
  textureKeep: number;   // 0..100
  blemishSoften: number; // 0..100
  skinToneEven: number;  // 0..100
};

export type BeautyParams = {
  brightness: number;    // -50..50
  eyeBright: number;     // 0..100
  teethWhite: number;    // 0..100
  softContrast: number;  // -50..50
};

export type EditParams = {
  liquify: LiquifyParams;
  skin: SkinParams;
  beauty: BeautyParams;
};
```

## 8. Landmark Provider

### Primary Provider

MediaPipe Face Landmarker / Face Mesh.

### Output Needed

```python
@dataclass
class FaceLandmarks:
    face_id: str
    bbox: tuple[float, float, float, float]
    points: np.ndarray  # shape: (N, 3), normalized or pixel coords
    confidence: float
    transform_matrix: Optional[np.ndarray]
```

### Coordinate Policy

- Store landmarks in normalized coordinates relative to source image size.
- Convert to pixel coordinates for preview/export size.
- Keep one canonical face id per detected face.

## 9. Mask Provider

### Masks

| Mask | Source |
|---|---|
| Face oval mask | Face oval landmarks |
| Skin mask | Face oval minus eyes/brows/lips/nostrils/hairline approximation |
| Eye mask | Eye landmarks |
| Mouth mask | Lip landmarks |
| Teeth candidate mask | Mouth region + color heuristic |

### Mask Format

- Single-channel float32 array `0.0-1.0`.
- Same size as processing image.
- Feathered edges.

## 10. Processing Order

```text
1. Decode image
2. Detect landmarks if missing
3. Build masks
4. Liquify image
5. Transform/rebuild masks for post-liquify image
6. Skin smoothing
7. Skin tone even
8. Blemish soften
9. Eye bright
10. Teeth white
11. Brightness/soft contrast
12. Encode output
```

## 11. Preview Quality Modes

| Mode | Use | Behavior |
|---|---|---|
| fast | slider drag | lower preview max side, cheaper filters |
| standard | slider release | full preview size, standard filters |
| export | final output | original size, best filters |

### Quality Settings

```python
QUALITY = {
    "fast": {
        "max_side_scale": 0.75,
        "filter_radius_scale": 0.75,
        "debug": False,
    },
    "standard": {
        "max_side_scale": 1.0,
        "filter_radius_scale": 1.0,
        "debug": False,
    },
    "export": {
        "max_side_scale": None,
        "filter_radius_scale": 1.0,
        "debug": False,
    },
}
```

## 12. Concurrency

### Preview Request Policy

- Each preview request has a monotonically increasing `request_id`.
- Engine may continue previous computation, but UI applies only latest response.
- Engine should cancel older preview jobs when possible.

### Export Policy

- One export job at a time per app instance.
- Export jobs have explicit `job_id`.
- Export supports cancellation.

## 13. Electron Security Settings

```ts
const mainWindow = new BrowserWindow({
  webPreferences: {
    preload: path.join(__dirname, 'preload.js'),
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
  },
});
```

## 14. Preload API

```ts
contextBridge.exposeInMainWorld('beautyApp', {
  engineHealth: () => ipcRenderer.invoke('engine:health'),
  openImage: () => ipcRenderer.invoke('file:openImage'),
  loadImage: (path: string) => ipcRenderer.invoke('engine:loadImage', path),
  renderPreview: (payload: PreviewRequest) => ipcRenderer.invoke('engine:preview', payload),
  exportImage: (payload: ExportRequest) => ipcRenderer.invoke('engine:export', payload),
  cancelJob: (jobId: string) => ipcRenderer.invoke('engine:cancelJob', jobId),
  onEngineEvent: (cb: (event: EngineEvent) => void) => {
    ipcRenderer.on('engine:event', (_, event) => cb(event));
  },
});
```

## 15. Diagnostics

Engine `health` returns:

```json
{
  "status": "ready",
  "version": "0.1.0",
  "platform": "windows",
  "python_version": "3.12.x",
  "available_backends": ["cpu", "cuda"],
  "active_backend": "cuda",
  "devices": [
    {"type":"cuda","name":"NVIDIA ...","available":true},
    {"type":"cpu","name":"CPU","available":true}
  ]
}
```

## 16. Development Environments

### macOS

- Node.js LTS.
- Python 3.11/3.12.
- PyTorch with MPS support.
- MediaPipe Python package.
- Xcode command line tools.

### Windows

- Node.js LTS.
- Python 3.11/3.12.
- PyTorch CUDA build when NVIDIA GPU is available.
- MediaPipe Python package.
- Visual Studio Build Tools for native packaging or future extensions.

## 17. Dependency Management

### JavaScript

Use npm or pnpm.

```bash
pnpm install
pnpm dev
pnpm build
```

### Python

Use uv or pip-tools.

```bash
uv venv
uv pip install -r requirements.txt
python -m beauty_engine.cli --health
```

## 18. Build Artifacts

```text
release/
  mac/
    Beauty Retouch Local.dmg
  win/
    Beauty Retouch Local Setup.exe
    Beauty Retouch Local Portable.zip
```

