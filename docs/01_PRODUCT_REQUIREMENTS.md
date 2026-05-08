# Product Requirements Document

## 1. Product Name

Working name: **PixMeat**

## 2. Product Goal

Build a minimal local portrait retouching desktop app with PixelCake-like slider-based controls for liquify, beauty enhancement, and skin smoothing.

The app focuses on fast, natural, controllable portrait edits. It avoids a large photo-editing feature set and concentrates on high-quality local processing.

## Current Implementation Status

The current repository implements the V1 face-retouching path on the CPU backend:

- Open/load/preview/export flows are wired through Electron and the Python engine.
- Face edits are active-face only.
- Liquify uses inverse MLS dense warp with control handles and foldover diagnostics.
- Skin retouch uses refined skin masks, guided filtering, texture restoration, blemish softening, and Lab tone evening.
- CUDA, MPS, and OpenCV CUDA are health/diagnostic probes only; they are not yet used by the processing pipeline.
- Body reshape, human parsing, pose analysis, RAW, batch, plugins, and cloud processing remain future work.

## 3. V1 Target Users

### Primary User

A creator, photographer, or small studio operator who wants fast one-click or slider-based portrait refinement on local files.

### Secondary User

A technically comfortable user who wants a local alternative to cloud-based retouching tools and accepts a focused interface.

## 4. V1 Core Jobs

1. Open a portrait image.
2. Automatically detect a face.
3. Adjust face shape through sliders.
4. Smooth skin while preserving texture.
5. Apply simple beauty adjustments.
6. Preview edits quickly.
7. Export a final image.

## 5. V1 Product Scope

### Included in V1

| Area | Feature |
|---|---|
| File | Open image, save/export image |
| View | Fit, zoom, pan, before, after, split view |
| Face | Auto-detect face, select active face when multiple faces exist |
| Liquify | Face slim, jawline, chin, eye enlarge, nose slim, smile |
| Skin | Smooth, texture keep, blemish soften, skin tone even |
| Beauty | Brightness, eye brighten, teeth whiten, mild contrast |
| Presets | Built-in presets, save user preset, reset |
| Performance | Preview cache, full-resolution export |
| Backends | CPU processing, CUDA/MPS/OpenCV CUDA diagnostics and future acceleration targets |
| Packaging | macOS app, Windows installer/portable build |

### Later Versions

| Area | Future Feature |
|---|---|
| Photoshop | UXP plugin |
| Batch | Batch import and batch export |
| RAW | RAW decoding and color workflow |
| Body | Body reshape |
| Makeup | Makeup transfer and detailed facial makeup |
| AI inpaint | Object removal and background replacement |
| Cloud | Optional remote GPU processing |

## 6. Platform Requirements

### macOS

- Support Apple Silicon Macs.
- Support Intel Macs through CPU fallback.
- Use CPU processing in the current version.
- Use MPS/Metal acceleration after operation implementations are added and the backend confirms availability.
- Ship as a `.dmg` or `.zip` app bundle.

### Windows

- Support Windows x64.
- Use CPU processing in the current version.
- Use CUDA acceleration after operation implementations are added and NVIDIA/CUDA runtime is available.
- Ship as `.exe` installer and optional portable build.

## 7. Local Processing Requirement

All image analysis and image transformation run on the user's machine. V1 stores all temporary files locally. The application should run without an internet connection after installation.

## 8. Input and Output Scope

### Input Formats

| Format | V1 Behavior |
|---|---|
| JPG/JPEG | Supported |
| PNG | Supported |
| WebP | Supported when Pillow supports it in bundled runtime |
| TIFF | Supported basic 8-bit/16-bit paths where libraries allow |
| RAW | Later version |
| PSD | Later version |

### Output Formats

| Format | V1 Behavior |
|---|---|
| JPEG | Supported, quality selectable |
| PNG | Supported |
| TIFF | Optional V1 export target; implement after JPEG/PNG |

## 9. Core Editing Parameters

### Liquify Parameters

| Parameter | Range | Default | Meaning |
|---|---:|---:|---|
| `face_slim` | 0-100 | 0 | Move cheek/jaw contours toward face center |
| `jawline` | 0-100 | 0 | Sharpen and lift jaw contour |
| `chin_length` | -50 to 50 | 0 | Shorten or lengthen chin vertically |
| `eye_enlarge` | 0-100 | 0 | Enlarge both eyes locally |
| `nose_slim` | 0-100 | 0 | Narrow nose wing and bridge region |
| `smile` | 0-100 | 0 | Lift mouth corners subtly |

### Skin Parameters

| Parameter | Range | Default | Meaning |
|---|---:|---:|---|
| `skin_smooth` | 0-100 | 0 | Smooth low-frequency skin detail |
| `texture_keep` | 0-100 | 70 | Preserve high-frequency skin texture |
| `blemish_soften` | 0-100 | 0 | Reduce small spots and uneven marks |
| `skin_tone_even` | 0-100 | 0 | Even skin color variation |

### Beauty Parameters

| Parameter | Range | Default | Meaning |
|---|---:|---:|---|
| `brightness` | -50 to 50 | 0 | Adjust skin/global portrait brightness mildly |
| `eye_bright` | 0-100 | 0 | Brighten eye white and iris highlights |
| `teeth_white` | 0-100 | 0 | Reduce tooth yellow tint and lift brightness |
| `soft_contrast` | -50 to 50 | 0 | Mild portrait contrast curve |

## 10. Preview Behavior Requirements

1. The app creates a preview image with max side between 1200 and 1800 pixels.
2. Landmarks are detected once per loaded image and cached.
3. Slider drag updates preview with debounce.
4. Slider release triggers a higher-quality preview render.
5. Full-resolution export uses original image dimensions.
6. Preview and export results use the same parameter semantics.

## 11. Multi-Face Behavior

1. When one face is detected, that face becomes active.
2. When multiple faces are detected, the largest face becomes active by default.
3. The preview displays selectable face boxes.
4. Slider edits apply to the active face in V1.
5. An `apply_to_all_faces` option is available as an experimental flag after the primary face path is stable.

## 12. Quality Requirements

### Liquify Quality

- Face boundary blending should avoid obvious background distortion.
- Eyes, lips, eyebrows, and nostrils should preserve clear edges.
- Strong sliders should remain visually plausible.
- All shape edits should be deterministic with identical input and parameters.

### Skin Quality

- Skin smoothing should preserve pores and fine texture when `texture_keep` is high.
- Eyes, eyebrows, lips, hair, and nostrils should be protected from smoothing.
- Skin tone evenness should avoid plastic-looking flat color.

### Beauty Quality

- Eye brightening should affect eye region rather than surrounding skin.
- Teeth whitening should preserve mouth/lip color separation.
- Brightness and contrast should preserve highlight detail where possible.

## 13. Performance Requirements

The application should prioritize responsiveness over full-resolution instant rendering.

| Operation | Target Behavior |
|---|---|
| Image open | UI remains responsive |
| First face analysis | Progress indicator appears after 300 ms |
| Slider drag | Debounced preview update |
| Slider release | Standard preview render |
| Export | Background job with progress and cancel |

## 14. Privacy Requirements

1. The app does not upload user images in V1.
2. Temporary files are stored in the app cache directory.
3. User can clear cache from settings.
4. Logs avoid storing full image paths when privacy mode is enabled.

## 15. Success Metrics

### Functional

- All V1 sliders produce visible, stable, reversible edits.
- Exported result matches the final preview at equivalent resolution.
- App launches on macOS and Windows.
- Backend diagnostics work across CPU/CUDA/MPS/OpenCV CUDA scenarios.

### UX

- User can complete open → adjust → compare → export in under one minute.
- Default presets produce natural results.
- Reset behavior is clear and immediate.

### Engineering

- Engine can be tested independently through CLI.
- UI can be tested with mocked engine responses.
- Golden-image regression tests cover each algorithm group.
