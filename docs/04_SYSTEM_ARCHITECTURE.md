# System Architecture

## 1. Architecture Overview

The app uses Electron for desktop UI and a local Python engine for image analysis and image processing.

```text
┌───────────────────────────────────────────────────────────────────┐
│ Electron App                                                      │
│                                                                   │
│ ┌───────────────────────────┐     ┌─────────────────────────────┐ │
│ │ Renderer Process          │     │ Main Process                │ │
│ │ React UI                  │     │ App lifecycle               │ │
│ │ Canvas preview            │◄───►│ IPC bridge                  │ │
│ │ Sliders                   │     │ Python process manager      │ │
│ └───────────────────────────┘     └──────────────┬──────────────┘ │
└──────────────────────────────────────────────────┼────────────────┘
                                                   │ stdio JSON-RPC
                                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│ Python Local Engine                                                │
│                                                                   │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐ │
│ │ API Server   │ │ Job Manager  │ │ Image Processing Pipeline    │ │
│ └──────────────┘ └──────────────┘ └──────────────────────────────┘ │
│                                                                   │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐ │
│ │ Face Module  │ │ Mask Module  │ │ Accelerator Backends         │ │
│ └──────────────┘ └──────────────┘ └──────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## 2. Process Model

### Electron Renderer

Responsible for:

- Rendering UI.
- Managing slider state.
- Rendering image preview canvas.
- Sending commands through preload API.
- Displaying engine state and job progress.

### Electron Main

Responsible for:

- Starting and stopping Python engine.
- Managing application lifecycle.
- Reading/writing app settings.
- Handling file dialogs.
- Validating paths.
- Forwarding renderer requests to Python engine.
- Managing request ids and cancellation.

### Python Engine

Responsible for:

- Loading images.
- Creating preview images.
- Detecting faces and landmarks.
- Building masks.
- Running liquify, smoothing, beauty algorithms.
- Selecting CPU/CUDA/MPS backend.
- Exporting full-resolution result.

## 3. Recommended Communication Protocol

Use newline-delimited JSON-RPC over stdio.

### Reasoning

- No local port management.
- Lower security exposure.
- Easy to bundle.
- Easy to test with CLI.
- Works on macOS and Windows.

### Message Shape

```json
{"id":"req_001","method":"health","params":{}}
```

### Response Shape

```json
{"id":"req_001","ok":true,"result":{"status":"ready"}}
```

### Error Shape

```json
{"id":"req_001","ok":false,"error":{"code":"read_error","message":"Cannot open image"}}
```

## 4. Data Flow

### Open Image Flow

```text
Renderer
  → Main: open file dialog
  → Engine: load_image(image_path, preview_max_side)
  → Engine: read image, create preview, detect faces
  → Main: response with image_id, preview_path, faces
  → Renderer: display preview and face boxes
```

### Preview Flow

```text
Renderer slider change
  → Main: preview(image_id, active_face_id, params, quality)
  → Engine: process cached preview image
  → Engine: save result preview path
  → Renderer: display result if request id is latest
```

### Export Flow

```text
Renderer export
  → Main: choose output path
  → Engine: export(image_id, params, output_path)
  → Engine: process original image
  → Engine: emit progress events
  → Renderer: update progress modal
  → Engine: return success
```

## 5. Image Session Model

Each opened image creates an `ImageSession`.

```json
{
  "image_id": "img_20260508_000001",
  "source_path": "/path/to/input.jpg",
  "original_width": 6000,
  "original_height": 4000,
  "preview_width": 1600,
  "preview_height": 1067,
  "preview_path": "/cache/img_.../preview.png",
  "faces": [
    {
      "face_id": "face_1",
      "bbox": [120, 90, 420, 520],
      "landmarks_path": "/cache/img_.../face_1_landmarks.json",
      "confidence": 0.98
    }
  ],
  "created_at": "2026-05-08T12:00:00Z"
}
```

## 6. Cache Model

### Cache Directory

```text
app-cache/
  sessions/
    img_xxx/
      original_meta.json
      preview.png
      preview_result_req_xxx.png
      landmarks.json
      masks/
        face_1_skin.png
        face_1_face.png
      debug/
        warp_grid.png
        skin_mask.png
```

### Cache Rules

1. Source image remains at original path.
2. Preview and intermediate files are stored in app cache.
3. Export writes to user-selected path.
4. Cache cleanup removes old sessions by size and age.
5. Debug artifacts are generated only in developer mode.

## 7. Module Boundaries

```text
engine/beauty_engine/
  api.py             # JSON-RPC command handling
  session.py         # Image session lifecycle
  io.py              # image read/write
  face.py            # face detection and landmarks
  masks.py           # face/skin/eye/mouth masks
  liquify.py         # parameter → warp field
  warp.py            # CPU/GPU remap implementations
  smoothing.py       # skin smoothing
  beauty.py          # color/eye/teeth adjustments
  pipeline.py        # process order orchestration
  backends.py        # acceleration selection
  presets.py         # parameter schema helpers
  diagnostics.py     # health, device info
```

## 8. Image Processing Pipeline

```text
Input image
  ↓
Decode to RGB/RGBA array
  ↓
Detect faces and landmarks
  ↓
Create region masks
  ↓
Liquify active face
  ↓
Recompute or transform masks after liquify where needed
  ↓
Skin smoothing
  ↓
Beauty color adjustments
  ↓
Blend edited region with source
  ↓
Encode preview/export result
```

## 9. Backend Selection

```text
User setting: Auto
  ↓
Windows: try CUDA torch backend
  ↓
Windows: try OpenCV CUDA backend if installed
  ↓
macOS: try MPS torch backend
  ↓
Fallback: CPU OpenCV/NumPy backend
```

## 10. Preview and Export Consistency

The preview path and export path share the same parameter schema and same processing order.

Differences:

| Aspect | Preview | Export |
|---|---|---|
| Image size | Downscaled | Original size |
| Cache | Aggressive | Minimal intermediate |
| Quality | Fast or standard | High |
| Progress | Spinner | Progress modal |
| Cancellation | Superseded by latest request | Explicit cancel |

## 11. Failure Recovery

### Engine Crash

1. Electron main detects Python process exit.
2. UI status shows engine error.
3. User can click `Restart Engine`.
4. App restarts engine and reloads current image session where possible.

### Backend Failure

1. Backend operation catches exception.
2. Engine switches to CPU backend for the failed operation.
3. Engine reports backend fallback in diagnostics.
4. UI shows a non-blocking status message.

### Job Cancellation

1. UI sends `cancel_job` with job id.
2. Engine marks job cancelled.
3. Long loops check cancellation flag.
4. Temp output is deleted.

## 12. Security Architecture

### Electron

- `contextIsolation: true`
- `nodeIntegration: false`
- Preload exposes a narrow typed API.
- Renderer cannot access arbitrary Node APIs.

### Engine

- stdio protocol avoids network listening.
- File paths are passed from Electron main after validation.
- Engine reads/writes only approved paths for export and cache.

## 13. Logging

### Log Levels

| Level | Usage |
|---|---|
| debug | Development diagnostics |
| info | Engine status and jobs |
| warn | Backend fallback and recoverable issues |
| error | Processing failure |

### Privacy Mode

When privacy mode is enabled:

- Log file names only, not full paths.
- Avoid writing user image metadata except dimensions and format.
- Avoid debug mask output.

## 14. Threading and Jobs

### Electron Main

- Single app process.
- Handles UI commands quickly.
- Long work is delegated to Python engine.

### Python Engine

- API loop stays responsive.
- Preview jobs use a worker thread/process queue.
- Export jobs use dedicated job id and cancellation flag.
- GPU backend operations are serialized per device unless tested safe.

## 15. Future Extensibility

The architecture supports future features:

- Batch queue.
- Photoshop plugin calling same engine.
- AI inpainting module.
- RAW decoder module.
- Native CUDA/Metal kernels.
- Cloud backend adapter.

