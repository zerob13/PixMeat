# Packaging and Release Specification

## 1. Release Targets

| Platform | Artifact |
|---|---|
| macOS | `.dmg` and/or `.zip` app bundle |
| Windows | `.exe` installer and optional portable `.zip` |

## 2. Packaged App Contents

```text
Beauty Retouch Local.app / Beauty Retouch Local.exe
  ├─ Electron runtime
  ├─ Renderer bundle
  ├─ Main process bundle
  ├─ Python engine executable
  ├─ Python runtime dependencies
  ├─ MediaPipe model assets
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
  beauty_engine/api.py
```

Windows:

```powershell
cd engine
pyinstaller --clean --onefile `
  --name beauty-engine `
  beauty_engine/api.py
```

Actual PyInstaller spec should include MediaPipe model files and any dynamic libraries discovered during testing.

## 4. Electron Packaging

Use electron-builder.

### Example `electron-builder.yml`

```yaml
appId: com.local.beautyretouch
productName: Beauty Retouch Local
files:
  - app/main/dist/**
  - app/renderer/dist/**
  - package.json
extraResources:
  - from: engine/dist/beauty-engine${env.ENGINE_EXT}
    to: engine/beauty-engine${env.ENGINE_EXT}
  - from: engine/models
    to: engine/models
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

Dev mode can spawn Python with module args:

```ts
python -m beauty_engine.api
```

Packaged mode spawns engine executable directly.

## 6. Model Asset Path Resolution

Engine should read model path from env var when set:

```text
BEAUTY_ENGINE_MODEL_DIR=/path/to/resources/engine/models
```

Fallback to package-local `engine/models` in dev.

## 7. macOS Specifics

### App Paths

- Cache: `~/Library/Caches/Beauty Retouch Local`
- Settings: `~/Library/Application Support/Beauty Retouch Local`

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

- Cache: `%LOCALAPPDATA%\Beauty Retouch Local\Cache`
- Settings: `%APPDATA%\Beauty Retouch Local`

### CUDA Runtime

Preferred V1 strategy:

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
    "dev": "pnpm run dev:app",
    "dev:app": "electron-vite dev",
    "build": "pnpm run build:renderer && pnpm run build:main",
    "build:engine:mac": "bash scripts/build-engine.sh",
    "build:engine:win": "powershell -File scripts/build-engine.ps1",
    "package:mac": "electron-builder --mac",
    "package:win": "electron-builder --win"
  }
}
```

## 11. Release Checklist

### Pre-Build

- Python tests pass.
- TypeScript tests pass.
- Renderer builds.
- Engine `health` works.
- MediaPipe model files exist.
- Default presets exist.

### macOS Build

- App launches.
- Engine starts from resources.
- Open image works.
- Preview works.
- Export works.
- MPS/CPU backend status appears.
- Cache path works.

### Windows Build

- App launches.
- Engine starts from resources.
- Open image works.
- Preview works.
- Export works.
- CUDA/CPU backend status appears.
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
Beauty Retouch Local processes images on this device.
No cloud processing is used in this version.
```

## 15. Final V1 Release Criteria

- macOS app package verified.
- Windows app package verified.
- CPU backend verified on both platforms.
- CUDA verified on at least one Windows NVIDIA machine.
- MPS verified on at least one Apple Silicon machine.
- Export verified for JPEG and PNG.
- Critical visual QA passed.

