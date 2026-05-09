# Packaging and Release Specification

## 1. Release Targets

| Platform | Artifact |
|---|---|
| macOS | `.dmg` and/or `.zip` app bundle |
| Windows | `.exe` installer and optional portable `.zip` |

## 2. Packaged App Contents

```text
PixMeat.app / PixMeat.exe
  ├─ Electron runtime
  ├─ Renderer bundle
  ├─ Main process bundle
  ├─ Python engine executable
  ├─ Python runtime dependencies
  ├─ Python package dependencies
  ├─ Optional local Analysis V2 model assets
  └─ Default presets
```

## 3. Engine Packaging

### Recommended Tooling

Use PyInstaller first because it is mature and straightforward for bundling Python apps.

### Engine Binary Names

| Platform | Binary |
|---|---|
| macOS | `beauty-engine` |
| Windows | `beauty-engine.exe` |

### Engine Build Commands

macOS:

```bash
cd engine
pyinstaller --clean --onefile \
  --name beauty-engine \
  beauty_engine/cli_entry.py
```

Windows:

```powershell
cd engine
pyinstaller --clean --onefile `
  --name beauty-engine `
  beauty_engine/cli_entry.py
```

Actual PyInstaller spec should include MediaPipe package assets and any dynamic libraries discovered during testing. Optional Analysis V2 weights live under `engine/models` or another configured local model directory.

## 4. Electron Packaging

Use electron-builder.

### Example `electron-builder.yml`

```yaml
appId: local.pixmeat.app
productName: PixMeat
files:
  - app/main/dist/**
  - app/renderer/dist/**
  - package.json
extraResources:
  - from: engine/dist/beauty-engine.exe
    to: engine/beauty-engine.exe
  - from: engine/beauty_engine
    to: engine/beauty_engine
    filter:
      - "**/*"
      - "!**/__pycache__/**"
      - "!**/*.pyc"
  - from: engine/requirements.txt
    to: engine/requirements.txt
  - from: engine/pyproject.toml
    to: engine/pyproject.toml
  - from: engine/models
    to: engine/models
    filter:
      - "**/*"
mac:
  target:
    - dmg
    - zip
  category: public.app-category.photography
win:
  target:
    - nsis
    - portable
nsis:
  oneClick: false
  perMachine: false
  allowToChangeInstallationDirectory: true
```

## 5. Packaged Engine Path Resolution

Electron main should resolve engine path differently in dev and packaged modes.

```ts
function getEnginePath(): string {
  if (app.isPackaged) {
    const name = process.platform === 'win32' ? 'beauty-engine.exe' : 'beauty-engine';
    return path.join(process.resourcesPath, 'engine', name);
  }
  return path.join(repoRoot, 'engine', '.venv', 'bin', 'python');
}
```

Dev mode automatically prefers `engine/.venv/bin/python` on macOS/Linux or `engine/.venv/Scripts/python.exe` on Windows when the venv exists. Otherwise it falls back to `PIXMEAT_PYTHON`, `python`, or `python3` with module args:

```ts
python -m beauty_engine.api
```

Packaged mode spawns the engine executable with `serve`, matching the CLI entry point.

## 6. Model Asset Path Resolution

Analysis V2 never downloads model weights at runtime. The engine reads explicit model paths from JSON-RPC config, then environment variables, then package-local discovery under `engine/models`:

```text
PIXMEAT_MODEL_DIR=/path/to/resources/engine/models
BEAUTY_ENGINE_MODEL_DIR=/path/to/resources/engine/models
PIXMEAT_FACE_LANDMARKER_MODEL=/path/to/face_landmarker.task
PIXMEAT_PERSON_SEGMENTATION_MODEL=/path/to/selfie_segmenter.task
PIXMEAT_HUMAN_PARSING_MODEL=/path/to/schp.onnx
```

Electron main sets `PIXMEAT_MODEL_DIR` to the packaged `engine/models` path when the caller has not already provided it.

## 7. macOS Specifics

### App Paths

- Cache: `~/Library/Caches/PixMeat`
- Settings: `~/Library/Application Support/PixMeat`

### Signing and Notarization

For public distribution, prepare:

- Developer ID Application certificate.
- Hardened runtime where compatible.
- Notarization workflow.

### Apple Silicon and Intel

Options:

1. Build separate Apple Silicon and Intel packages.
2. Build universal package if all binary dependencies support it.

V1 can start with Apple Silicon and Windows x64 as primary test machines, with Intel Mac CPU fallback validation when available.

## 8. Windows Specifics

### App Paths

- Cache: `%LOCALAPPDATA%\PixMeat\Cache`
- Settings: `%APPDATA%\PixMeat`

### CUDA Runtime

Future acceleration strategy:

1. Use PyTorch package that bundles compatible CUDA runtime components when installed in the engine environment.
2. Detect CUDA availability at runtime.
3. Fall back to CPU when CUDA is unavailable.

The installer should not require users to manually configure CUDA for basic use.

### Code Signing

For public distribution, prepare Windows code signing certificate.

## 9. Auto Update

V1 can ship manual updates. Auto-update enters later after signing is stable.

Future options:

- electron-updater.
- GitHub Releases.
- Custom update server.

## 10. Build Scripts

### Root Scripts

```json
{
  "scripts": {
    "dev": "electron-vite dev",
    "build": "tsc --noEmit && electron-vite build",
    "test": "vitest run && pnpm test:engine",
    "test:engine": "python -m pytest engine/tests",
    "dist": "pnpm build && electron-builder"
  }
}
```

## 11. Release Checklist

### Pre-Build

- Python tests pass.
- TypeScript tests pass.
- Renderer builds.
- Engine `health` works.
- MediaPipe package assets are bundled or excluded safely.
- Default presets exist.

### macOS Build

- App launches.
- Engine starts from resources.
- Open image works.
- Preview works.
- Export works.
- CPU backend status appears; MPS diagnostics appear when available.
- Cache path works.

### Windows Build

- App launches.
- Engine starts from resources.
- Open image works.
- Preview works.
- Export works.
- CPU backend status appears; CUDA/OpenCV CUDA diagnostics appear when available.
- Cache path works.

### Visual QA

- Test with frontal portrait.
- Test with side-angle portrait.
- Test with smile/teeth visible portrait.
- Test with multiple faces.
- Test with no face.
- Test strong slider values.

## 12. Versioning

Use semantic versioning.

```text
0.1.0  first internal prototype
0.2.0  full V1 feature set
0.3.0  acceleration preview
1.0.0  public V1 release
```

## 13. Crash and Log Collection

V1 writes local logs only.

```text
logs/
  app.log
  engine.log
```

Privacy mode redacts full file paths.

## 14. Distribution Notes

The packaged app should include a simple first-run notice:

```text
PixMeat processes images on this device.
No cloud processing is used in this version.
```

## 15. Final V1 Release Criteria

- macOS app package verified.
- Windows app package verified.
- CPU backend verified on both platforms.
- CUDA diagnostics verified on at least one Windows NVIDIA machine.
- MPS diagnostics verified on at least one Apple Silicon machine.
- Export verified for JPEG and PNG.
- Critical visual QA passed.
