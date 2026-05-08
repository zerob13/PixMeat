# PixMeat — Documentation Pack

## Project Summary

This project is a cross-platform local portrait retouching desktop application focused on three core capabilities:

1. Parameter-based liquify
2. Beauty enhancement
3. Skin smoothing

The application provides PixelCake-like slider controls while keeping processing local. V1 targets macOS and Windows. The current implementation is CPU-first; CUDA/MPS/OpenCV CUDA are probed and exposed in diagnostics, but the active image-processing pipeline currently runs through NumPy/OpenCV CPU code.

- Windows: CPU processing today, CUDA/OpenCV CUDA probe and future acceleration target
- macOS: CPU processing today, MPS probe and future acceleration target
- Both platforms: CPU fallback remains mandatory

## Current Implementation Snapshot

As of the current codebase:

1. Electron + React UI opens images, shows preview, sliders, presets, compare modes, settings, and export flow.
2. Python engine exposes stdio JSON-RPC plus CLI commands for `health`, `process`, and `debug-masks`.
3. Supported image IO uses Pillow with EXIF transpose and RGB float32 processing.
4. Face analysis tries MediaPipe Face Mesh, then Haar detection, then skin/heuristic fallback. Haar boxes are expanded for safer face-local edits.
5. Liquify uses parameterized face handles, boundary anchors, inverse MLS dense warp maps, OpenCV `remap`, single-pass blending, and foldover debug output.
6. Skin retouch uses a refined skin mask, guided filtering, base/detail reconstruction, conservative blemish softening, and Lab tone evening.
7. Debug artifacts include landmarks, face mask, initial skin mask, refined skin mask, eye mask, mouth mask, warp grid, control handles, liquify mask, and foldover heatmap.
8. Test coverage currently includes renderer state/components plus engine params, IO, masks, warp, liquify, smoothing, beauty, pipeline, API, and demo E2E tests.

## V1 Product Positioning

A lightweight local portrait retouching tool for photographers, creators, and small studios. The product should feel closer to a focused retouching utility than a full image editor.

## V1 Platform Scope

| Platform | V1 Scope |
|---|---|
| macOS Apple Silicon | Supported |
| macOS Intel | Supported through CPU fallback |
| Windows x64 | Supported |
| Windows + NVIDIA GPU | CPU processing today; CUDA diagnostics and future acceleration target |
| Linux | Later version |
| Photoshop plugin | Later version |
| RAW workflow | Later version |
| Cloud processing | Later version |

## Technology Direction

| Layer | Choice |
|---|---|
| Desktop shell | Electron |
| UI | React + TypeScript |
| Local engine | Python |
| Image processing | OpenCV + NumPy CPU pipeline |
| Face landmarks | MediaPipe Face Mesh when available, Haar/skin/heuristic fallback |
| GPU acceleration | CUDA/MPS/OpenCV CUDA diagnostics only; processing acceleration is future work |
| Packaging | electron-builder + bundled Python engine |

## Documentation Index

| File | Purpose |
|---|---|
| `01_PRODUCT_REQUIREMENTS.md` | Product goals, V1 scope, users, success criteria |
| `02_FUNCTION_BEHAVIOR_SPEC.md` | Detailed behavior for every feature |
| `03_UI_UX_SPEC.md` | UI layout, states, interaction behavior, ASCII wireframes |
| `04_SYSTEM_ARCHITECTURE.md` | Process model, modules, data flow, storage |
| `05_TECHNICAL_SPEC.md` | Stack, runtime choices, dependency strategy |
| `06_ALGORITHM_SPEC.md` | Liquify, masks, skin smoothing, beauty algorithms |
| `07_ENGINE_API_SPEC.md` | Electron ↔ Python engine protocol |
| `08_ACCELERATION_AND_BACKENDS.md` | CPU/CUDA/MPS backend strategy |
| `09_PROJECT_STRUCTURE.md` | Repository structure and module boundaries |
| `10_DEVELOPMENT_PLAN.md` | Milestones and implementation order |
| `11_TASK_BREAKDOWN.md` | Codex-ready task list with acceptance criteria |
| `12_TEST_PLAN.md` | Unit, integration, visual, performance tests |
| `13_PACKAGING_RELEASE.md` | macOS/Windows packaging and release requirements |
| `15_REFERENCES.md` | Official references and source links |
| `AGENTS.md` | Coding rules for Codex/agents |

## High-Level V1 Acceptance Criteria

The V1 build is acceptable when all of the following are true:

1. User can open a JPG, PNG, WebP, or TIFF image.
2. App detects the main face and overlays optional face bounding boxes.
3. User can adjust liquify sliders and see a preview.
4. User can adjust smoothing and beauty sliders and see a preview.
5. User can reset individual groups and reset all parameters.
6. User can compare before/after using split view and toggle view.
7. User can export a full-resolution result.
8. App runs on macOS and Windows.
9. App reports CUDA, MPS, OpenCV CUDA, and CPU availability; current processing remains CPU unless a future backend implements the operation.
10. Processing remains fully local.

## Recommended First Implementation Path

1. Implement Python CLI engine first.
2. Implement CPU algorithms first.
3. Add Electron UI and local process bridge.
4. Add preview cache and debounced slider rendering.
5. Add torch/OpenCV CUDA operation implementations behind the backend interface.
6. Add packaging for macOS and Windows.
