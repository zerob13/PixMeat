# PixMeat

PixMeat is a local portrait retouching desktop app built with Electron, React, TypeScript, and a Python image-processing engine. Images stay on the local machine; the Electron UI talks to the Python engine over stdio JSON-RPC and passes image file paths instead of image bytes.

## Requirements

- Node.js 20+
- pnpm 9+
- Python 3.11 or 3.12
- macOS or Windows for the desktop app

Python 3.13 is not recommended yet because the optional MediaPipe dependency is pinned to Python versions below 3.13.

## Setup

Install JavaScript dependencies:

```bash
pnpm install
```

Create and populate the Python engine environment:

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m beauty_engine.cli health
python -m pytest
```

On Windows, use:

```powershell
cd engine
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m beauty_engine.cli health
python -m pytest
```

In development the Electron main process automatically uses `engine/.venv` when it exists. You can still override the Python executable explicitly:

```bash
export PIXMEAT_PYTHON="$PWD/engine/.venv/bin/python"
```

## Development

Run the desktop app:

```bash
pnpm dev
```

Run checks:

```bash
pnpm test:ui
cd engine && .venv/bin/python -m pytest
pnpm lint
```

Run the engine CLI directly:

```bash
cd engine
.venv/bin/python -m beauty_engine.cli process ../demo/before.jpg /tmp/pixmeat-out.jpg --debug-dir /tmp/pixmeat-debug
.venv/bin/python -m beauty_engine.cli analyze ../demo/before.jpg /tmp/pixmeat-analysis --analysis-version v2
```

## Analysis V2

Analysis V2 is selectable through engine config and environment variables. It adds model-backed slots for face detection, landmarks, person segmentation, human parsing, semantic skin masks, body regions, and debug overlays. Missing model paths never trigger network downloads; the engine records diagnostics and degrades to deterministic CPU geometry. Legacy skin/background face guesses are disabled by default.

Enable it for the Python engine:

```bash
export PIXMEAT_ANALYSIS_VERSION=v2
export PIXMEAT_ANALYSIS_DEBUG=true
export PIXMEAT_ANALYSIS_DEBUG_DIR=/tmp/pixmeat-analysis
export PIXMEAT_MODEL_DIR=/absolute/path/to/local/models
```

Or pass model paths in JSON-RPC:

```json
{
  "analysis": {
    "version": "v2",
    "debug": true,
    "device": "auto",
    "model_paths": {
      "face_detector": "/models/scrfd.onnx",
      "face_landmarker": "/models/face_landmarker.task",
      "person_segmentation": "/models/selfie_segmenter.task",
      "human_parsing": "/models/schp.onnx"
    }
  }
}
```

See `docs/analysis_v2.md` for output schema, degraded behavior, and debug overlay meanings.

## Build And Package

Build TypeScript and renderer/main bundles:

```bash
pnpm build
```

Build a standalone Python engine binary before packaging when needed:

```bash
./scripts/build-engine.sh
```

Windows:

```powershell
.\scripts\build-engine.ps1
```

Create Electron packages:

```bash
pnpm dist
```

Packaged builds include the Python engine source and requirements. If a standalone `engine/dist/beauty-engine` binary is present, `electron-builder.yml` can bundle it under Electron resources.
