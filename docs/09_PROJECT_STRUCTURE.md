# Project Structure Specification

## 1. Repository Layout

```text
beauty-retouch-local/
├─ package.json
├─ pnpm-lock.yaml
├─ electron-builder.yml
├─ tsconfig.json
├─ README.md
├─ AGENTS.md
│
├─ app/
│  ├─ main/
│  │  ├─ main.ts
│  │  ├─ windows.ts
│  │  ├─ menu.ts
│  │  ├─ engineProcess.ts
│  │  ├─ engineRpc.ts
│  │  ├─ fileDialogs.ts
│  │  ├─ settingsStore.ts
│  │  └─ ipcHandlers.ts
│  │
│  ├─ preload/
│  │  └─ preload.ts
│  │
│  └─ renderer/
│     ├─ index.html
│     ├─ src/
│     │  ├─ main.tsx
│     │  ├─ App.tsx
│     │  ├─ components/
│     │  │  ├─ EditorLayout.tsx
│     │  │  ├─ CanvasViewer.tsx
│     │  │  ├─ SliderPanel.tsx
│     │  │  ├─ SliderControl.tsx
│     │  │  ├─ PresetMenu.tsx
│     │  │  ├─ ExportDialog.tsx
│     │  │  ├─ SettingsDialog.tsx
│     │  │  └─ StatusBar.tsx
│     │  ├─ state/
│     │  │  ├─ editorStore.ts
│     │  │  ├─ settingsStore.ts
│     │  │  └─ presetStore.ts
│     │  ├─ types/
│     │  │  ├─ engine.ts
│     │  │  ├─ params.ts
│     │  │  └─ ui.ts
│     │  ├─ utils/
│     │  │  ├─ debounce.ts
│     │  │  ├─ imagePaths.ts
│     │  │  └─ valueMapping.ts
│     │  └─ styles/
│     │     └─ app.css
│     │
│     └─ vite.config.ts
│
├─ engine/
│  ├─ pyproject.toml
│  ├─ requirements.txt
│  ├─ beauty_engine/
│  │  ├─ __init__.py
│  │  ├─ api.py
│  │  ├─ cli.py
│  │  ├─ protocol.py
│  │  ├─ session.py
│  │  ├─ jobs.py
│  │  ├─ io.py
│  │  ├─ face.py
│  │  ├─ landmark_indices.py
│  │  ├─ masks.py
│  │  ├─ liquify.py
│  │  ├─ warp.py
│  │  ├─ smoothing.py
│  │  ├─ beauty.py
│  │  ├─ pipeline.py
│  │  ├─ backends/
│  │  │  ├─ __init__.py
│  │  │  ├─ base.py
│  │  │  ├─ cpu.py
│  │  │  ├─ torch_backend.py
│  │  │  └─ opencv_cuda.py
│  │  ├─ diagnostics.py
│  │  ├─ params.py
│  │  ├─ presets.py
│  │  └─ errors.py
│  │
│  ├─ models/
│  │  └─ README.md
│  │
│  └─ tests/
│     ├─ test_params.py
│     ├─ test_masks.py
│     ├─ test_liquify.py
│     ├─ test_pipeline.py
│     └─ fixtures/
│
├─ scripts/
│  ├─ dev-start.ts
│  ├─ build-engine.sh
│  ├─ build-engine.ps1
│  ├─ package-mac.sh
│  └─ package-win.ps1
│
├─ docs/
│  └─ copied-docs-from-this-pack/
│
└─ release/
```

## 2. Electron Main Modules

### `engineProcess.ts`

Responsibilities:

- Locate Python engine executable in dev and packaged modes.
- Spawn engine process.
- Restart engine.
- Stop engine on app quit.
- Capture stdout/stderr.
- Forward engine events to renderer.

### `engineRpc.ts`

Responsibilities:

- Create request ids.
- Send JSON lines to engine stdin.
- Parse JSON lines from engine stdout.
- Map responses to pending promises.
- Handle timeouts.
- Handle engine events.

### `ipcHandlers.ts`

Responsibilities:

- Register renderer IPC handlers.
- Validate renderer payloads.
- Call engine RPC.
- Return typed responses.

### `fileDialogs.ts`

Responsibilities:

- Open image dialog.
- Export file dialog.
- Restrict output paths through user selection.

### `settingsStore.ts`

Responsibilities:

- Read/write JSON settings.
- Provide defaults.
- Handle schema migration.

## 3. Renderer Modules

### `EditorLayout.tsx`

- Three-column layout.
- Handles empty/editor/error states.

### `CanvasViewer.tsx`

- Loads preview image path.
- Renders before/after/split.
- Handles zoom and pan.
- Draws face boxes.
- Sends face selection callback.

### `SliderPanel.tsx`

- Groups sliders.
- Handles reset group.
- Triggers parameter change.

### `SliderControl.tsx`

- Generic controlled slider.
- Numeric input.
- Keyboard support.

### `ExportDialog.tsx`

- Export format and quality selection.
- Progress modal.
- Cancel button.

### `StatusBar.tsx`

- Engine status.
- Active backend.
- Preview render state.
- Image dimensions.

## 4. Python Engine Modules

### `api.py`

- stdio JSON-RPC loop.
- Method dispatch.
- Error serialization.
- Event emission.

### `protocol.py`

- Typed request/response models.
- Validation helpers.

### `session.py`

- ImageSession class.
- Session registry.
- Cache paths.
- Preview metadata.

### `jobs.py`

- Preview/export job management.
- Cancellation flags.
- Progress events.

### `io.py`

- Decode and encode images.
- Metadata handling.
- Preview resizing.

### `face.py`

- MediaPipe model initialization.
- Face detection.
- Landmark conversion.
- Face bbox calculation.

### `landmark_indices.py`

- Region index constants.
- Region utility helpers.

### `masks.py`

- Face mask.
- Skin mask.
- Eye/mouth masks.
- Feathering and morphology.

### `liquify.py`

- Parameter mapping.
- Control point generation.
- Dense flow generation.
- Piecewise affine fallback.

### `warp.py`

- CPU remap.
- Torch grid remap.
- OpenCV CUDA remap wrapper.

### `smoothing.py`

- Skin smoothing.
- Frequency separation.
- Blemish soften.
- Tone even.

### `beauty.py`

- Brightness.
- Soft contrast.
- Eye bright.
- Teeth white.

### `pipeline.py`

- Preview/export orchestration.
- Stage ordering.
- Progress callbacks.

### `backends/base.py`

- Backend interface.
- Operation support registry.

### `backends/cpu.py`

- CPU implementation.

### `backends/torch_backend.py`

- CUDA/MPS torch implementation.

### `backends/opencv_cuda.py`

- Optional OpenCV CUDA implementation.

## 5. Type Boundaries

### Renderer ↔ Main

Use TypeScript types.

### Main ↔ Engine

Use JSON-compatible types only:

- string
- number
- boolean
- null
- arrays
- objects

Image data is passed by file path, not base64.

### Engine Internal

Use Python dataclasses or Pydantic models for validation.

## 6. Naming Conventions

### TypeScript

- Components: PascalCase.
- Hooks: `useSomething`.
- Types: PascalCase.
- Files: camelCase for modules, PascalCase for React components.

### Python

- Modules: snake_case.
- Classes: PascalCase.
- Functions: snake_case.
- Constants: UPPER_SNAKE_CASE.

## 7. Config Files

### App Settings JSON

```json
{
  "preferredBackend": "auto",
  "previewMaxSide": 1600,
  "showFaceBoxes": true,
  "cacheLimitGb": 2,
  "privacyMode": false
}
```

### Preset JSON

```json
{
  "id": "preset_natural",
  "name": "Natural",
  "params": {
    "liquify": {
      "faceSlim": 8,
      "jawline": 5,
      "chinLength": 0,
      "eyeEnlarge": 6,
      "noseSlim": 0,
      "smile": 0
    },
    "skin": {
      "skinSmooth": 25,
      "textureKeep": 75,
      "blemishSoften": 10,
      "skinToneEven": 15
    },
    "beauty": {
      "brightness": 5,
      "eyeBright": 8,
      "teethWhite": 0,
      "softContrast": 4
    }
  }
}
```

## 8. Development Commands

### Root

```bash
pnpm install
pnpm dev
pnpm test
pnpm build
```

### Engine

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m beauty_engine.cli health
python -m pytest
```

### Packaged Engine

```bash
python -m PyInstaller engine/beauty_engine/api.py --name beauty-engine
```

Actual PyInstaller spec should be customized after dependency verification.

## 9. Build Modes

| Mode | Electron | Python Engine |
|---|---|---|
| Dev | Vite dev server | Python source process |
| Staging | Built renderer | PyInstaller engine |
| Release | Packaged app | Bundled engine executable |

## 10. Asset Locations

### Dev Mode

```text
engine/models/
app/renderer/assets/
```

### Packaged Mode

```text
resources/
  engine/
    beauty-engine.exe or beauty-engine
    models/
```

## 11. Cache Locations

Use OS app data directories.

| Platform | Cache Root |
|---|---|
| macOS | `~/Library/Caches/Beauty Retouch Local` |
| Windows | `%LOCALAPPDATA%/Beauty Retouch Local/Cache` |

## 12. Source Control Ignore

```gitignore
node_modules/
dist/
release/
app/renderer/dist/
engine/.venv/
engine/build/
engine/dist/
engine/__pycache__/
.cache/
*.pyc
.DS_Store
```

