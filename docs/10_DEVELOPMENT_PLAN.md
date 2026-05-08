# Development Plan

## 1. Delivery Strategy

Build the app in vertical slices. Each milestone should produce a runnable artifact.

Recommended order:

1. Python engine CLI.
2. CPU image algorithms.
3. Electron shell and UI.
4. Engine bridge.
5. Preview workflow.
6. Export workflow.
7. Acceleration backends.
8. Packaging.
9. QA and release polish.

## 2. Milestone Overview

| Milestone | Name | Outcome |
|---|---|---|
| M0 | Repository scaffold | Project builds empty Electron app and Python engine health CLI |
| M1 | Engine CPU prototype | CLI processes one image with landmarks, liquify, smoothing |
| M2 | UI prototype | Electron opens image, shows canvas, sliders update local state |
| M3 | Engine bridge | UI calls Python engine and renders preview result |
| M4 | Complete V1 features | All sliders, presets, compare, export |
| M5 | Acceleration | CUDA/MPS backend selection and torch operations |
| M6 | Packaging | macOS and Windows builds |
| M7 | QA polish | Visual tests, performance, crash recovery, settings |

## 3. M0 — Repository Scaffold

### Goals

- Create monorepo.
- Create Electron + React app.
- Create Python engine package.
- Add basic health command.
- Add development scripts.

### Deliverables

- `pnpm dev` launches Electron shell.
- `python -m beauty_engine.cli health` prints JSON.
- `engineRpc.ts` can call `health` in dev.

### Acceptance Criteria

- App starts on macOS and Windows dev machines.
- Engine process starts and returns health.
- Basic CI-style test command exists.

## 4. M1 — Engine CPU Prototype

### Goals

- Load image.
- Detect face landmarks.
- Generate masks.
- Implement CPU liquify and skin smoothing.
- CLI process command outputs image.

### Deliverables

```bash
python -m beauty_engine.cli process input.jpg output.jpg --face-slim 30 --skin-smooth 40
```

### Acceptance Criteria

- Output file is created.
- Face slim produces visible change.
- Skin smoothing produces visible change.
- Landmark debug overlay can be generated.
- Mask debug output can be generated.

## 5. M2 — UI Prototype

### Goals

- Build main layout.
- Implement image open.
- Implement canvas viewer.
- Implement sliders.
- Implement before/after state mock.

### Deliverables

- Empty state.
- Editor state.
- Right slider panel.
- Status bar.
- Mock preview update.

### Acceptance Criteria

- User can open image and view it.
- User can zoom/pan.
- Sliders update values.
- Preset menu can apply mock values.

## 6. M3 — Engine Bridge

### Goals

- Implement stdio JSON-RPC.
- Implement `load_image`.
- Implement `render_preview`.
- Renderer displays processed preview.
- Request token prevents stale preview updates.

### Deliverables

- Electron UI connected to Python engine.
- Slider changes render actual processed preview.

### Acceptance Criteria

- Load image returns preview and faces.
- Slider change updates processed preview.
- Latest request wins during rapid slider changes.
- UI shows backend status.

## 7. M4 — Complete V1 Features

### Goals

- All liquify sliders.
- All skin sliders.
- All beauty sliders.
- Face selection.
- Presets.
- Compare modes.
- Export.

### Deliverables

- Functional V1 feature set.

### Acceptance Criteria

- Every slider has a visible and bounded effect.
- Reset group and reset all work.
- Built-in presets work.
- User preset save/load works.
- Export outputs full-resolution result.
- Multi-face image allows active face selection.

## 8. M5 — Acceleration

### Goals

- Implement backend abstraction.
- Add torch CUDA backend.
- Add torch MPS backend.
- Add operation-level fallback.
- Add diagnostics UI.

### Deliverables

- `health` reports available backends.
- Settings can choose backend.
- Pipeline can run on CPU/CUDA/MPS where supported.

### Acceptance Criteria

- Windows NVIDIA machine reports CUDA.
- Apple Silicon machine reports MPS.
- CPU fallback works on all target machines.
- Backend failure falls back without crashing app.

## 9. M6 — Packaging

### Goals

- Bundle Python engine.
- Package macOS build.
- Package Windows build.
- Include model assets.
- Validate packaged mode paths.

### Deliverables

- macOS `.dmg` or `.zip`.
- Windows installer and portable build.

### Acceptance Criteria

- Packaged app launches.
- Engine executable starts from app resources.
- Image open, preview, export work in packaged app.
- Settings and cache paths resolve correctly.

## 10. M7 — QA and Polish

### Goals

- Improve visual quality.
- Add golden-image tests.
- Add performance diagnostics.
- Add crash recovery.
- Improve error UX.

### Deliverables

- Test suite.
- Debug mode.
- Release checklist.

### Acceptance Criteria

- Unit tests cover params, masks, algorithms.
- Golden tests cover core sliders.
- App handles engine restart.
- Export cancellation works.
- Visual regressions are tracked.

## 11. Implementation Sequence by Week-Like Blocks

This is an ordering guide rather than a calendar commitment.

### Block 1 — Scaffold

- Create repo.
- Electron app.
- Python package.
- JSON-RPC health.

### Block 2 — Landmarks and Masks

- Image load.
- Face landmarks.
- Face/skin/eye/mouth masks.
- Debug rendering.

### Block 3 — Core Algorithms

- CPU remap.
- Face slim.
- Eye enlarge.
- Skin smoothing.
- Brightness.

### Block 4 — Full Sliders

- Jawline.
- Chin.
- Nose.
- Smile.
- Texture keep.
- Tone even.
- Eye bright.
- Teeth white.

### Block 5 — UI Integration

- Canvas.
- Sliders.
- Debounced preview.
- Active face selection.
- Compare modes.

### Block 6 — Export and Presets

- Full-res export.
- Export dialog.
- Built-in presets.
- User presets.
- Settings.

### Block 7 — Acceleration

- Backend probe.
- Torch remap.
- Torch blur.
- CUDA/MPS selection.
- Diagnostics.

### Block 8 — Packaging and QA

- PyInstaller engine.
- electron-builder config.
- macOS package.
- Windows package.
- Visual regression tests.

## 12. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| MediaPipe packaging complexity | App packaging delay | Build engine package early |
| MPS op compatibility varies | Mac acceleration gaps | Per-operation CPU fallback |
| OpenCV CUDA bundle complexity | Windows acceleration delay | Torch CUDA backend first |
| Liquify artifacts | Visual quality issue | Boundary anchors + masks + debug grid |
| Skin mask roughness | Plastic or smeared result | Conservative masks + feature exclusions |
| Out-of-order preview responses | UI flicker | Request token latest-wins policy |
| Large image memory | Export crash | Preview scaling + export memory checks + optional tiling |

## 13. Feature Freeze Criteria

V1 enters feature freeze when:

1. All V1 sliders are implemented.
2. Preview/export are connected.
3. macOS and Windows packaged builds work.
4. CPU backend passes tests.
5. Backend diagnostics work.

## 14. Release Candidate Criteria

Release candidate is ready when:

1. Golden-image tests pass.
2. Manual QA checklist passes on macOS and Windows.
3. Engine crash recovery works.
4. Export cancellation works.
5. App cache cleanup works.
6. No critical visual artifacts in test portraits.

