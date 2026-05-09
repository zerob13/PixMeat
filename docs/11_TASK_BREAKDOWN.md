# Codex-Ready Task Breakdown

## Task Format

Each task should be implemented as a small vertical change with tests where applicable.

Status note: Epics A-H are largely implemented for the current CPU product. Analysis V2 is the default analysis path, body and face shape sliders are bidirectional, and Epic I is probe-only. Packaging and deeper QA remain active work. Keep task statuses updated when implementation changes.

Task fields:

- Goal
- Files to create or edit
- Implementation details
- Acceptance criteria

## Epic A — Repository and Tooling

### A1. Create Monorepo Scaffold

**Goal:** Create project structure for Electron app and Python engine.

**Files:**

```text
package.json
pnpm-workspace.yaml
app/main/main.ts
app/preload/preload.ts
app/renderer/src/App.tsx
engine/pyproject.toml
engine/beauty_engine/__init__.py
engine/beauty_engine/cli.py
```

**Implementation Details:**

- Use Electron + Vite + React + TypeScript.
- Use Python package under `engine/beauty_engine`.
- Add root scripts: `dev`, `build`, `test`.

**Acceptance Criteria:**

- `pnpm dev` opens Electron window.
- `python -m beauty_engine.cli health` outputs JSON.

### A2. Add TypeScript Strict Types

**Goal:** Add shared TypeScript types for params, engine responses, UI state.

**Files:**

```text
app/renderer/src/types/params.ts
app/renderer/src/types/engine.ts
app/renderer/src/types/ui.ts
```

**Acceptance Criteria:**

- TypeScript build passes.
- Parameter defaults are typed.

### A3. Add Python Test Setup

**Goal:** Add pytest and initial unit tests.

**Files:**

```text
engine/tests/test_params.py
engine/beauty_engine/params.py
```

**Acceptance Criteria:**

- `pytest` runs.
- Parameter clamping tests pass.

## Epic B — Engine Protocol

### B1. Implement JSON-RPC Loop

**Goal:** Implement newline-delimited JSON-RPC over stdin/stdout.

**Files:**

```text
engine/beauty_engine/api.py
engine/beauty_engine/protocol.py
engine/beauty_engine/errors.py
```

**Implementation Details:**

- Read one line JSON.
- Dispatch by method.
- Write one line JSON response.
- Support success and error envelopes.

**Acceptance Criteria:**

- `health` request returns valid response.
- Invalid JSON returns error response.
- Unknown method returns `unknown_method` error.

### B2. Implement Electron Engine Process Manager

**Goal:** Start Python engine from Electron main.

**Files:**

```text
app/main/engineProcess.ts
app/main/engineRpc.ts
app/main/ipcHandlers.ts
```

**Acceptance Criteria:**

- Electron main can call `health`.
- Renderer can display engine status.
- Engine stderr is captured for diagnostics.

### B3. Implement Request Timeout and Latest-Wins Token

**Goal:** Prevent stale preview responses from updating UI.

**Files:**

```text
app/main/engineRpc.ts
app/renderer/src/state/editorStore.ts
```

**Acceptance Criteria:**

- Preview response with older token is ignored.
- Timeout creates a clear error response.

## Epic C — Image IO and Session

### C1. Implement Image Decode/Encode

**Goal:** Load and save common image formats.

**Files:**

```text
engine/beauty_engine/io.py
engine/tests/test_io.py
```

**Implementation Details:**

- Use Pillow first.
- Convert to RGB float32 0..1.
- Preserve alpha as optional side channel.

**Acceptance Criteria:**

- JPG and PNG fixtures load.
- PNG export works.
- JPEG export quality option works.

### C2. Implement ImageSession Registry

**Goal:** Create session object for opened image.

**Files:**

```text
engine/beauty_engine/session.py
```

**Acceptance Criteria:**

- `load_image` creates `image_id`.
- Preview image is cached.
- Session can be retrieved by id.

### C3. Implement `load_image` API

**Goal:** Connect image load command to session and preview.

**Files:**

```text
engine/beauty_engine/api.py
engine/beauty_engine/session.py
```

**Acceptance Criteria:**

- `load_image` returns preview path and dimensions.
- Unsupported format returns `unsupported_format`.

## Epic D — Face Landmarks and Masks

### D1. Add MediaPipe Face Detection

**Goal:** Detect face landmarks in preview image.

**Files:**

```text
engine/beauty_engine/face.py
engine/beauty_engine/landmark_indices.py
engine/tests/test_face.py
```

**Acceptance Criteria:**

- Portrait fixture returns at least one face.
- Face bbox and landmark count are returned.
- Zero-face image returns empty faces list.

### D2. Add Landmark Debug Overlay

**Goal:** Render landmarks to debug image.

**Files:**

```text
engine/beauty_engine/debug.py
engine/beauty_engine/cli.py
```

**Acceptance Criteria:**

- CLI can output `landmarks.png`.
- Landmark index groups are visually inspectable.

### D3. Implement Face Mask

**Goal:** Build feathered face oval mask.

**Files:**

```text
engine/beauty_engine/masks.py
engine/tests/test_masks.py
```

**Acceptance Criteria:**

- Face mask is float32 0..1.
- Face mask shape matches image shape.
- Mask has soft edges.

### D4. Implement Skin, Eye, Mouth Masks

**Goal:** Build protected masks for smoothing and beauty.

**Files:**

```text
engine/beauty_engine/masks.py
```

**Acceptance Criteria:**

- Skin mask excludes eyes, lips, brows.
- Eye mask covers both eyes.
- Mouth mask covers lip/mouth region.

## Epic E — Liquify

### E1. Implement CPU Remap and MLS Utility

**Goal:** Implement dense map remap with OpenCV plus inverse MLS map generation.

**Files:**

```text
engine/beauty_engine/warp.py
engine/tests/test_warp.py
```

**Acceptance Criteria:**

- Identity map returns image within tolerance.
- Simple translation map shifts image as expected.
- MLS identity maps are stable.
- MLS inverse translation maps target pixels back to source coordinates.

### E2. Implement Face Shape with Bidirectional Handles

**Goal:** Add signed face shape parameter.

**Files:**

```text
engine/beauty_engine/liquify.py
engine/beauty_engine/pipeline.py
```

**Acceptance Criteria:**

- `face_slim=0` changes nothing.
- `face_slim=0.3` visibly slims face.
- `face_slim=-0.3` visibly widens face.
- Background outside face mask remains stable.
- Slider target handles are included in a single inverse MLS remap.

### E3. Implement Eye Size

**Goal:** Add local signed eye size control.

**Files:**

```text
engine/beauty_engine/liquify.py
```

**Acceptance Criteria:**

- Positive values enlarge both eyes symmetrically.
- Negative values shrink both eyes symmetrically.
- Eye center remains stable.
- Eyebrows stay mostly stable.

### E4. Implement Jawline and Chin

**Goal:** Add jawline and chin length controls.

**Files:**

```text
engine/beauty_engine/liquify.py
```

**Acceptance Criteria:**

- Jawline changes lower face contour.
- Chin slider changes chin height.
- Mouth remains stable.

### E5. Implement Nose Width and Smile

**Goal:** Add signed nose width and mouth corner controls.

**Files:**

```text
engine/beauty_engine/liquify.py
```

**Acceptance Criteria:**

- Positive nose values reduce nose width and negative values widen it.
- Positive smile values lift mouth corners and negative values lower them.
- High values remain bounded.

### E6. Add Liquify Debug Outputs

**Goal:** Visualize warp field.

**Files:**

```text
engine/beauty_engine/debug.py
```

**Acceptance Criteria:**

- Debug output shows warp grid, control handles, liquify mask, and foldover heatmap.
- Grid and heatmap help identify excessive distortion.

## Epic F — Skin and Beauty

### F1. Implement Skin Smoothing

**Goal:** Add refined-mask guided skin smoothing with texture keep.

**Files:**

```text
engine/beauty_engine/smoothing.py
engine/tests/test_smoothing.py
```

**Acceptance Criteria:**

- Smooth value changes skin region.
- Refined skin mask is available in debug output.
- Texture keep controls high-frequency return.
- Protected regions remain stable.

### F2. Implement Skin Tone Even

**Goal:** Smooth skin chroma variation.

**Files:**

```text
engine/beauty_engine/smoothing.py
```

**Acceptance Criteria:**

- Skin redness/unevenness reduces.
- Lips and eyes are protected.

### F3. Implement Blemish Soften

**Goal:** Conservative blemish detection and softening.

**Files:**

```text
engine/beauty_engine/smoothing.py
```

**Acceptance Criteria:**

- Small spots are softened.
- Large facial features remain stable.
- Debug mask is available.

### F4. Implement Brightness and Contrast

**Goal:** Add mild curve-based brightness and soft contrast.

**Files:**

```text
engine/beauty_engine/beauty.py
```

**Acceptance Criteria:**

- Positive/negative values work.
- Clipping is limited.

### F5. Implement Eye Bright

**Goal:** Brighten eye region.

**Files:**

```text
engine/beauty_engine/beauty.py
```

**Acceptance Criteria:**

- Eye whites brighten.
- Surrounding skin changes minimally.

### F6. Implement Teeth White

**Goal:** Whiten visible teeth conservatively.

**Files:**

```text
engine/beauty_engine/beauty.py
```

**Acceptance Criteria:**

- Teeth brighten and yellow tint reduces.
- Lips retain original color.
- Closed-mouth portraits change minimally.

## Epic G — Pipeline and Preview

### G1. Implement Processing Pipeline

**Goal:** Orchestrate liquify, skin, beauty stages.

**Files:**

```text
engine/beauty_engine/pipeline.py
```

**Acceptance Criteria:**

- Pipeline accepts image, landmarks, masks, params.
- Pipeline returns processed image.
- Stage order matches spec.

### G2. Implement `render_preview`

**Goal:** Process cached preview through pipeline.

**Files:**

```text
engine/beauty_engine/api.py
```

**Acceptance Criteria:**

- Preview result file is created.
- Response includes elapsed time and backend.

### G3. Implement `export_image`

**Goal:** Full-resolution export.

**Files:**

```text
engine/beauty_engine/api.py
engine/beauty_engine/jobs.py
```

**Acceptance Criteria:**

- Export writes selected output path.
- Progress events fire per stage.
- Cancel request stops job.

## Epic H — Electron UI

### H1. Build Editor Layout

**Goal:** Create empty/editor states.

**Files:**

```text
app/renderer/src/components/EditorLayout.tsx
app/renderer/src/App.tsx
```

**Acceptance Criteria:**

- Empty state shows open action.
- Editor layout has canvas and right panel.

### H2. Implement Canvas Viewer

**Goal:** Display image, zoom, pan, face boxes.

**Files:**

```text
app/renderer/src/components/CanvasViewer.tsx
```

**Acceptance Criteria:**

- Image fits viewport.
- Zoom/pan works.
- Face boxes render and can be selected.

### H3. Implement Slider Panel

**Goal:** Create all V1 sliders.

**Files:**

```text
app/renderer/src/components/SliderPanel.tsx
app/renderer/src/components/SliderControl.tsx
```

**Acceptance Criteria:**

- All sliders display correct ranges.
- Sliders update editor store.
- Reset group works.

### H4. Connect Sliders to Preview

**Goal:** Debounced render preview.

**Files:**

```text
app/renderer/src/state/editorStore.ts
app/renderer/src/utils/debounce.ts
```

**Acceptance Criteria:**

- Dragging slider updates preview.
- Latest request wins.
- Preview loading indicator appears.

### H5. Implement Compare Modes

**Goal:** Before, after, split views.

**Files:**

```text
app/renderer/src/components/CanvasViewer.tsx
```

**Acceptance Criteria:**

- Before/after toggle works.
- Split divider can be dragged.
- Zoom/pan persists across modes.

### H6. Implement Presets

**Goal:** Built-in and user presets.

**Files:**

```text
app/renderer/src/components/PresetMenu.tsx
app/renderer/src/state/presetStore.ts
```

**Acceptance Criteria:**

- Built-in presets apply.
- User preset saves and persists.
- Reset preset works.

### H7. Implement Export Dialog

**Goal:** Export full-resolution result.

**Files:**

```text
app/renderer/src/components/ExportDialog.tsx
app/main/fileDialogs.ts
```

**Acceptance Criteria:**

- User selects output path.
- Export progress displays.
- Cancel button works.

## Epic I — Backends and Acceleration

### I1. Add Backend Base Class

**Goal:** Add backend interface and selection.

**Files:**

```text
engine/beauty_engine/backends/base.py
engine/beauty_engine/backends/cpu.py
engine/beauty_engine/diagnostics.py
```

**Acceptance Criteria:**

- CPU backend selected by default.
- Health reports CPU.

### I2. Add Torch CUDA/MPS Backend

**Goal:** Add torch tensor operations for remap and blur.

**Current Status:** Only CUDA/MPS availability probes exist in `torch_backend.py`; operation implementations are not done.

**Files:**

```text
engine/beauty_engine/backends/torch_backend.py
```

**Acceptance Criteria:**

- CUDA probe works on Windows NVIDIA machine.
- MPS probe works on Apple Silicon machine.
- Operation fallback works.

### I3. Add Backend Settings UI

**Goal:** Allow user to choose backend.

**Files:**

```text
app/renderer/src/components/SettingsDialog.tsx
app/main/settingsStore.ts
```

**Acceptance Criteria:**

- Auto/CPU/CUDA/MPS/OpenCV CUDA options are visible where supported by UI.
- Health updates active backend diagnostics.
- Processing remains CPU until backend operation dispatch is implemented.

## Epic J — Packaging and Release

### J1. Bundle Python Engine

**Goal:** Build engine executable.

**Files:**

```text
scripts/build-engine.sh
scripts/build-engine.ps1
```

**Acceptance Criteria:**

- Engine executable can run `health`.
- Packaged engine includes models.

### J2. Configure electron-builder

**Goal:** Package macOS and Windows apps.

**Files:**

```text
electron-builder.yml
package.json
```

**Acceptance Criteria:**

- macOS package builds.
- Windows package builds.
- Packaged app finds engine executable.

### J3. Add Release Checklist

**Goal:** Add manual QA checklist.

**Files:**

```text
release-checklist.md
```

**Acceptance Criteria:**

- Checklist covers launch, open, sliders, export, backend, settings.
