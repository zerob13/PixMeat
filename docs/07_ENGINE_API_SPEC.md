# Engine API Specification

## 1. Protocol

Use newline-delimited JSON-RPC over stdin/stdout between Electron main process and Python engine.

Each request is one JSON object followed by newline.
Each response is one JSON object followed by newline.
Engine events are also one JSON object followed by newline and use `type: "event"`.

## 2. Request Envelope

```json
{
  "id": "req_000001",
  "method": "health",
  "params": {}
}
```

## 3. Success Response Envelope

```json
{
  "id": "req_000001",
  "ok": true,
  "result": {}
}
```

## 4. Error Response Envelope

```json
{
  "id": "req_000001",
  "ok": false,
  "error": {
    "code": "read_error",
    "message": "Cannot open image",
    "details": {}
  }
}
```

## 5. Event Envelope

```json
{
  "type": "event",
  "event": "job_progress",
  "payload": {
    "job_id": "job_001",
    "progress": 0.42,
    "stage": "skin_smoothing"
  }
}
```

## 6. Methods

## 6.1 `health`

### Request

```json
{"id":"req_1","method":"health","params":{}}
```

### Response

```json
{
  "id": "req_1",
  "ok": true,
  "result": {
    "status": "ready",
    "version": "0.1.0",
    "platform": "darwin",
    "python_version": "3.12.0",
    "available_backends": ["cpu", "mps"],
    "active_backend": "mps",
    "devices": [
      {"type":"mps","name":"Apple GPU","available":true},
      {"type":"cpu","name":"CPU","available":true}
    ]
  }
}
```

### Behavior

- Returns engine state.
- Performs lightweight backend probes for CPU, CUDA, MPS, and OpenCV CUDA.
- Does not load image models unless already initialized.
- Current image processing remains CPU even when non-CPU devices are reported.

## 6.2 `set_backend`

### Request

```json
{
  "id": "req_2",
  "method": "set_backend",
  "params": {
    "backend": "auto"
  }
}
```

### Valid Backend Values

- `auto`
- `cpu`
- `cuda`
- `mps`
- `opencv_cuda`

### Response

```json
{
  "id": "req_2",
  "ok": true,
  "result": {
    "active_backend": "cuda",
    "fallback_backend": "cpu"
  }
}
```

### Behavior

- Updates active backend preference for diagnostics/status.
- Runs availability probe.
- Falls back to CPU when requested backend is unavailable.
- Current processing operations do not yet dispatch to CUDA/MPS/OpenCV CUDA implementations.

## 6.3 `load_image`

### Request

```json
{
  "id": "req_3",
  "method": "load_image",
  "params": {
    "image_path": "/path/to/input.jpg",
    "preview_max_side": 1600,
    "detect_faces": true
  }
}
```

### Response

```json
{
  "id": "req_3",
  "ok": true,
  "result": {
    "image_id": "img_abc123",
    "source_path": "/path/to/input.jpg",
    "preview_path": "/cache/img_abc123/preview.png",
    "width": 6000,
    "height": 4000,
    "preview_width": 1600,
    "preview_height": 1067,
    "faces": [
      {
        "face_id": "face_1",
        "bbox": [350, 120, 520, 650],
        "confidence": 0.98,
        "landmark_count": 468
      }
    ],
    "active_face_id": "face_1"
  }
}
```

### Behavior

- Reads image.
- Creates preview image.
- Detects faces when requested.
- Stores session metadata.
- Returns preview path for renderer.

## 6.4 `get_session`

### Request

```json
{
  "id": "req_4",
  "method": "get_session",
  "params": {
    "image_id": "img_abc123"
  }
}
```

### Response

```json
{
  "id": "req_4",
  "ok": true,
  "result": {
    "image_id": "img_abc123",
    "preview_path": "/cache/img_abc123/preview.png",
    "faces": [],
    "active_face_id": null
  }
}
```

## 6.5 `render_preview`

### Request

```json
{
  "id": "req_5",
  "method": "render_preview",
  "params": {
    "image_id": "img_abc123",
    "request_token": "preview_00042",
    "active_face_id": "face_1",
    "quality": "standard",
    "params": {
      "liquify": {
        "face_slim": 0.25,
        "jawline": 0.1,
        "chin_length": 0.0,
        "eye_enlarge": 0.15,
        "nose_slim": 0.0,
        "smile": 0.0
      },
      "skin": {
        "skin_smooth": 0.4,
        "texture_keep": 0.7,
        "blemish_soften": 0.1,
        "skin_tone_even": 0.2
      },
      "beauty": {
        "brightness": 0.05,
        "eye_bright": 0.1,
        "teeth_white": 0.0,
        "soft_contrast": 0.05
      }
    }
  }
}
```

### Response

```json
{
  "id": "req_5",
  "ok": true,
  "result": {
    "request_token": "preview_00042",
    "image_id": "img_abc123",
    "preview_result_path": "/cache/img_abc123/preview_preview_00042.png",
    "width": 1600,
    "height": 1067,
    "backend": "mps",
    "elapsed_ms": 312
  }
}
```

### Behavior

- Processes cached preview image.
- Saves result image to cache.
- Returns path.
- Older preview tokens can be cancelled or superseded.

## 6.6 `export_image`

### Request

```json
{
  "id": "req_6",
  "method": "export_image",
  "params": {
    "image_id": "img_abc123",
    "job_id": "job_export_001",
    "active_face_id": "face_1",
    "output_path": "/path/to/output.jpg",
    "format": "jpeg",
    "quality": 92,
    "keep_metadata": true,
    "params": {
      "liquify": {},
      "skin": {},
      "beauty": {}
    }
  }
}
```

### Progress Events

```json
{
  "type": "event",
  "event": "job_progress",
  "payload": {
    "job_id": "job_export_001",
    "progress": 0.15,
    "stage": "loading_original"
  }
}
```

### Final Response

```json
{
  "id": "req_6",
  "ok": true,
  "result": {
    "job_id": "job_export_001",
    "output_path": "/path/to/output.jpg",
    "backend": "cuda",
    "elapsed_ms": 2300
  }
}
```

### Behavior

- Uses original image dimensions.
- Uses same pipeline as preview.
- Writes to output path only after successful processing.
- Uses temp file and atomic move when possible.

## 6.7 `cancel_job`

### Request

```json
{
  "id": "req_7",
  "method": "cancel_job",
  "params": {
    "job_id": "job_export_001"
  }
}
```

### Response

```json
{
  "id": "req_7",
  "ok": true,
  "result": {
    "job_id": "job_export_001",
    "cancel_requested": true
  }
}
```

## 6.8 `debug_render_masks`

Developer-mode method.

### Request

```json
{
  "id": "req_8",
  "method": "debug_render_masks",
  "params": {
    "image_id": "img_abc123",
    "face_id": "face_1"
  }
}
```

### Response

```json
{
  "id": "req_8",
  "ok": true,
  "result": {
    "paths": {
      "landmarks": "/cache/img_abc123/debug/landmarks.png",
      "face_mask": "/cache/img_abc123/debug/face_mask.png",
      "skin_mask": "/cache/img_abc123/debug/skin_mask.png",
      "refined_skin_mask": "/cache/img_abc123/debug/refined_skin_mask.png"
    }
  }
}
```

## 7. Error Codes

| Code | Meaning |
|---|---|
| `engine_not_ready` | Engine still initializing |
| `unsupported_format` | Input image format unsupported |
| `read_error` | Image read failed |
| `write_error` | Export write failed |
| `image_not_found` | Unknown image id |
| `face_not_found` | Unknown face id |
| `no_face` | Face-dependent edit requested without face |
| `backend_unavailable` | Requested backend unavailable |
| `processing_error` | Algorithm failed |
| `job_cancelled` | Job cancelled |
| `invalid_params` | Parameter schema invalid |
| `unknown_method` | Unsupported JSON-RPC method |

## 8. Parameter Validation

Engine clamps normalized values:

```python
face_slim = clamp(face_slim, 0.0, 1.0)
jawline = clamp(jawline, 0.0, 1.0)
chin_length = clamp(chin_length, -1.0, 1.0)
```

Invalid or missing groups use defaults.

## 9. Engine Event Types

| Event | Payload |
|---|---|
| `engine_ready` | health result |
| `engine_error` | error code/message |
| `backend_changed` | active backend |
| `job_progress` | job id/progress/stage |
| `job_cancelled` | job id |
| `job_completed` | job id/output path |

## 10. CLI Compatibility

The same engine should support CLI processing:

```bash
python -m beauty_engine.cli health
python -m beauty_engine.cli process input.jpg output.jpg --face-slim 30 --skin-smooth 40
python -m beauty_engine.cli debug-masks input.jpg debug_dir/
```

CLI helps algorithm tests and Codex implementation.
