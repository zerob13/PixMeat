# Test Plan

## 1. Test Goals

1. Ensure algorithms produce stable, bounded edits.
2. Ensure UI and engine communicate reliably.
3. Ensure preview/export behavior is consistent.
4. Ensure macOS and Windows builds work.
5. Ensure acceleration fallback behaves safely.

## 2. Test Categories

| Category | Scope |
|---|---|
| Unit tests | Params, masks, warp/MLS, liquify, smoothing, beauty, IO |
| Integration tests | Engine API and pipeline |
| Visual regression tests | Golden image comparisons |
| UI tests | Renderer state and interaction |
| Packaging tests | macOS/Windows packaged app |
| Manual QA | Visual quality and edge cases |

## 3. Python Unit Tests

### `test_params.py`

Cases:

- Default params are valid.
- UI values convert to normalized values.
- Out-of-range values are clamped.
- Missing groups use defaults.

### `test_io.py`

Cases:

- Load JPG.
- Load PNG.
- Load image with alpha.
- Export JPEG.
- Export PNG.
- Unsupported extension returns expected error.

### `test_masks.py`

Cases:

- Face mask shape matches image.
- Mask values are 0..1.
- Skin mask is smaller than face mask.
- Eye/lip protected masks reduce skin mask.
- Feathering creates intermediate alpha values.

### `test_warp.py`

Cases:

- Identity warp returns original within tolerance.
- Translation warp moves content.
- Masked blend affects only mask region.
- MLS identity maps are stable.
- MLS inverse translation maps target pixels back to source coordinates.

### `test_liquify.py`

Cases:

- Zero params return near-original result.
- Face slim changes cheek pixels.
- Eye enlarge changes eye region.
- Strong params remain within output bounds.
- Multi-face active face selection affects expected region.
- Protected regions change less than editable cheek/jaw regions.

### `test_smoothing.py`

Cases:

- Smooth zero returns near-original.
- Smooth high reduces local variance in skin mask.
- Texture keep high preserves high-frequency detail.
- Protected regions remain stable.
- Strong edges remain protected during smoothing.

### `test_beauty.py`

Cases:

- Brightness positive increases average luminance.
- Brightness negative decreases average luminance.
- Eye bright affects eye candidate region.
- Teeth white affects teeth candidate region when present.

### Backend Probe Coverage

Current backend probes are covered through health/API tests rather than a dedicated `test_backend.py`.

- CPU backend is always available in `health`.
- CUDA, MPS, and OpenCV CUDA missing-device cases return unavailable instead of failing.
- Operation fallback tests should be added when backend operation dispatch exists.

## 4. Engine API Integration Tests

### Health

Request:

```json
{"id":"1","method":"health","params":{}}
```

Expected:

- `ok: true`
- `status: ready`
- `active_backend` exists

### Load Image

Expected:

- Returns `image_id`.
- Returns preview path.
- Preview path exists.
- Faces array is valid.

### Render Preview

Expected:

- Returns preview result path.
- Path exists.
- Response includes elapsed time.
- Unknown image id returns `image_not_found`.

### Export

Expected:

- Writes output path.
- Emits progress events.
- Cancel path returns `job_cancelled` or stops job.

## 5. Visual Regression Tests

## 5.1 Golden Fixture Set

Create a local fixture set with usage rights cleared:

```text
tests/fixtures/
  portrait_front_01.jpg
  portrait_side_01.jpg
  portrait_smile_01.jpg
  portrait_multi_face_01.jpg
  portrait_low_light_01.jpg
  portrait_no_face_01.jpg
```

## 5.2 Golden Outputs

For each fixture, store outputs for representative params:

```text
golden/
  portrait_front_01/
    face_slim_30.png
    eye_enlarge_30.png
    skin_smooth_40.png
    natural_preset.png
```

## 5.3 Comparison Metrics

Use a combination:

- Mean absolute error threshold.
- SSIM threshold for deterministic CPU tests.
- Region-specific checks.
- Human review for visual quality.

GPU outputs may differ slightly from CPU. Use looser tolerance for CUDA/MPS tests.

Current golden-image tests are not yet committed. The demo E2E test uses `demo/before.jpg` as a local anchor and verifies that the primary portrait face is selected and the pipeline produces output/debug artifacts.

## 6. UI Tests

### Renderer Unit Tests

- Slider default values render.
- Slider values clamp.
- Reset group works.
- Preset application updates state.
- Before/after mode changes state.

### IPC Mock Tests

- `loadImage` success populates editor state.
- `renderPreview` response updates after image.
- Old preview token is ignored.
- Engine error displays toast.

### Canvas Interaction Tests

- Fit mode computes correct scale.
- Zoom changes scale around cursor.
- Pan updates offset.
- Face box click selects face id.

## 7. Manual QA Checklist

## 7.1 Launch

- App opens.
- Engine status becomes ready.
- Active backend appears.
- Settings open.

## 7.2 Open Image

- JPG opens.
- PNG opens.
- Large image opens.
- No-face image opens with disabled face controls.
- Multi-face image shows selectable boxes.

## 7.3 Liquify

- Face slim natural at 20-35.
- Jawline natural at 20-35.
- Chin positive and negative work.
- Eye enlarge natural at 10-25.
- Nose slim natural at 10-25.
- Smile natural at 10-25.
- Reset liquify restores shape.

## 7.4 Skin

- Smooth reduces unevenness.
- Texture keep restores skin detail.
- Tone even reduces redness.
- Blemish soften handles small spots conservatively.
- Eyes/lips remain sharp.

## 7.5 Beauty

- Brightness curve feels mild.
- Eye bright avoids surrounding skin.
- Teeth white affects visible teeth.
- Soft contrast produces mild pop.

## 7.6 Compare

- Before mode shows original.
- After mode shows processed preview.
- Split mode divider works.
- Zoom/pan remains stable.

## 7.7 Export

- Export JPEG works.
- Export PNG works.
- Export cancel works.
- Output file opens.
- Output reflects current params.

## 7.8 Backend

- CPU backend works.
- CUDA backend works on Windows NVIDIA test machine.
- MPS backend works on Apple Silicon test machine where supported.
- Backend fallback does not crash.

## 8. Performance Benchmarks

Record elapsed time for:

| Operation | Fixture | Metric |
|---|---|---|
| Load image | 24MP JPEG | ms |
| Face detection | 1600px preview | ms |
| Preview render | 1600px preview | ms |
| Export | 24MP JPEG | ms |
| Slider drag | continuous | dropped frames / perceived lag |

Benchmark outputs should be saved as JSON:

```json
{
  "platform": "win32",
  "backend": "cuda",
  "image": "portrait_front_01",
  "preview_ms": 240,
  "export_ms": 3200
}
```

## 9. Error Tests

| Case | Expected Behavior |
|---|---|
| Engine unavailable | UI shows engine error and restart action |
| Invalid image path | Error response and toast |
| Backend crash | CPU fallback and warning |
| Export path unavailable | Export error |
| Cancel export | Job stops and temp output removed |
| Stale preview response | UI ignores it |

## 10. Release Test Matrix

| Platform | CPU | CUDA | MPS | Packaged App |
|---|---|---|---|---|
| macOS Apple Silicon | Yes | N/A | Yes | Yes |
| macOS Intel | Yes | N/A | N/A | Yes |
| Windows x64 no NVIDIA | Yes | N/A | N/A | Yes |
| Windows x64 NVIDIA | Yes | Yes | N/A | Yes |

## 11. Acceptance Thresholds

### Functional

- 100% V1 slider coverage.
- 100% engine API method coverage.
- All critical manual QA items pass.

### Quality

- No obvious face boundary tear in standard portraits.
- No smoothing spill into eyes/lips in standard portraits.
- No crash during repeated open/preview/export cycles.

### Performance

- UI remains responsive during preview/export.
- Preview uses debounced rendering.
- Export shows progress.
