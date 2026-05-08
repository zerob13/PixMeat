# AGENTS.md

## Project Mission

Implement a local portrait retouching desktop application with Electron UI and Python image-processing engine.

## Core Rules

1. Implement CPU backend first.
2. Keep all image processing inside Python engine.
3. Keep Electron renderer sandboxed.
4. Pass images by file path across IPC/RPC.
5. Keep preview and export parameter semantics identical.
6. Keep each algorithm module independently testable.
7. Add tests for parameter validation, masks, warp, pipeline, and API.
8. Prefer deterministic algorithms.
9. Use operation-level fallback for CUDA/MPS backend issues.
10. Use English for code, comments, commit messages, and identifiers.

## Implementation Priorities

1. Correctness.
2. Visual naturalness.
3. Responsiveness.
4. GPU acceleration.
5. Packaging polish.

## Expected Commands

```bash
pnpm install
pnpm dev
pnpm build

cd engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m beauty_engine.cli health
python -m pytest
```

On Windows, adapt virtual environment commands accordingly.

## Code Style

### TypeScript

- Use strict TypeScript.
- Use explicit exported types for API payloads.
- Keep renderer state in a typed store.
- Avoid direct Node API access in renderer.

### Python

- Use dataclasses or Pydantic-style validation for API models.
- Use NumPy arrays for image data.
- Use OpenCV for CPU image operations.
- Keep backend-specific code behind `ImageBackend` interface.
- Raise typed errors and serialize them through API layer.

## Testing Expectations

- Add unit tests for every algorithm module.
- Add at least one integration test for engine API.
- Add visual debug outputs for masks and landmarks.
- Use golden-image tests after initial algorithms are stable.

## UI Expectations

- Implement the UI described in `03_UI_UX_SPEC.md`.
- Keep first version minimal and functional.
- Focus on open image, sliders, preview, compare, export.

## Algorithm Expectations

- Use MediaPipe landmarks.
- Use soft masks for blending.
- Use face-local coordinate system for liquify.
- Use frequency separation or edge-preserving smoothing for skin.
- Protect eyes, eyebrows, lips, nostrils, and hairline from smoothing.

## Packaging Expectations

- Bundle Python engine into Electron resources.
- Validate dev and packaged engine path resolution.
- Keep macOS and Windows build configs separate where needed.

