# Codex Bootstrap Prompt

Use this prompt to start implementation with Codex.

---

You are implementing **Beauty Retouch Local**, a cross-platform local portrait retouching desktop app.

Read these files first:

1. `docs/00_README.md`
2. `docs/01_PRODUCT_REQUIREMENTS.md`
3. `docs/04_SYSTEM_ARCHITECTURE.md`
4. `docs/05_TECHNICAL_SPEC.md`
5. `docs/06_ALGORITHM_SPEC.md`
6. `docs/07_ENGINE_API_SPEC.md`
7. `docs/11_TASK_BREAKDOWN.md`
8. `AGENTS.md`

## Project Goal

Build a local desktop app with:

- Electron + React + TypeScript UI.
- Python local image-processing engine.
- Slider-based portrait liquify, skin smoothing, and beauty enhancement.
- macOS and Windows support.
- CUDA/MPS acceleration where available.
- CPU fallback everywhere.

## First Implementation Target

Implement the project in this order:

1. Repository scaffold.
2. Electron empty app.
3. Python engine package with `health` CLI.
4. JSON-RPC over stdio between Electron main and Python engine.
5. Image load and preview generation.
6. MediaPipe face landmarks.
7. Mask generation.
8. CPU liquify prototype: face slim and eye enlarge.
9. CPU skin smoothing prototype.
10. Electron UI sliders connected to preview.

## Constraints

- Keep image processing in Python engine.
- Pass image data by file path, not base64.
- Use JSON-compatible API payloads.
- Keep renderer sandboxed.
- Keep algorithm modules testable without Electron.
- Implement CPU path before GPU path.
- Add tests for each engine module.

## Acceptance Criteria for First Codex Pass

The first complete pass should support:

```bash
python -m beauty_engine.cli health
python -m beauty_engine.cli process input.jpg output.jpg --face-slim 30 --eye-enlarge 20 --skin-smooth 40
pnpm dev
```

The Electron app should:

1. Launch.
2. Show empty state.
3. Open an image.
4. Display preview.
5. Show slider panel.
6. Call Python engine health.

## Implementation Style

- Prefer simple, explicit code.
- Keep modules small.
- Avoid hidden global state except engine session registry.
- Add comments only where they clarify algorithmic choices.
- Use typed TypeScript and typed Python dataclasses where useful.
- Add debug image outputs for landmarks and masks.

## Start Task

Begin with Epic A and Epic B from `11_TASK_BREAKDOWN.md`.

Create the repository scaffold and implement:

- Electron + React + TypeScript shell.
- Python engine package.
- CLI `health` command.
- stdio JSON-RPC `health` method.
- Electron main process engine manager.
- Renderer status bar showing engine state.

After implementation, provide:

1. Files changed.
2. Commands to run.
3. Current limitations.
4. Next task recommendation from `11_TASK_BREAKDOWN.md`.

