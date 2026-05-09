# PixMeat

PixMeat is a local portrait retouching desktop app built with Electron, React, TypeScript, and a Python image-processing engine. Images stay on the local machine; the Electron UI talks to the Python engine over stdio JSON-RPC and passes image file paths instead of image bytes.

## Requirements

- Node.js 20+
- pnpm 9+
- macOS or Windows for the desktop app

Python 3.11 or 3.12 is useful for engine development, but it is no longer required just to run `pnpm dev` or a packaged app. PixMeat can generate a bundled uv/Python runtime under `engine/runtime`.

## Setup

Install JavaScript dependencies:

```bash
pnpm install
```

For engine development, create and populate the Python environment:

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

In development the Electron main process automatically uses `engine/.venv` when it exists. If it does not exist, `pnpm dev` runs `scripts/prepare-engine-runtime.mjs --if-missing`, which injects uv/Python with `tiny-runtime-injector` and installs `engine/requirements.txt` into `engine/runtime/venv`.

You can still override the Python executable explicitly:

```bash
export PIXMEAT_PYTHON="$PWD/engine/.venv/bin/python"
```

## Development

Run the desktop app:

```bash
pnpm dev
```

Prepare the bundled engine runtime explicitly:

```bash
pnpm engine:runtime
```

Run checks:

```bash
pnpm test:ui
pnpm test:engine
pnpm lint
```

`pnpm test:engine` uses `engine/.venv` when present and otherwise prepares/uses the bundled runtime under `engine/runtime/venv`.

Run the engine CLI directly:

```bash
cd engine
.venv/bin/python -m beauty_engine.cli process ../demo/before.jpg /tmp/pixmeat-out.jpg --debug-dir /tmp/pixmeat-debug
.venv/bin/python -m beauty_engine.cli analyze ../demo/before.jpg /tmp/pixmeat-analysis --analysis-version v2
```

## Analysis V2

Analysis V2 is the default analysis path and is still configurable through engine config and environment variables. It adds model-backed slots for face detection, landmarks, person segmentation, human parsing, semantic skin masks, body regions, and debug overlays. Missing model paths never trigger network downloads; the engine records diagnostics and degrades to deterministic CPU geometry. Legacy skin/background face guesses are disabled by default.

Configure it for the Python engine:

```bash
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

Build a standalone Python engine binary before packaging only when needed:

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

`pnpm dist` runs `pnpm engine:runtime` first. Packaged builds include the Python engine source, local models, the injected uv/Python runtime, and the installed Python dependencies. If a standalone `engine/dist/beauty-engine` binary is present, Electron still prefers that binary.
