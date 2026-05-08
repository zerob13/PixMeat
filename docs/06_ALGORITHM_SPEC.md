# Algorithm Specification

This document describes the current CPU implementation. Future body parsing, pose-driven body reshape, ARAP mesh warp, and GPU operation implementations are future work and must not be treated as current behavior.

## 1. Current Pipeline

```text
RGB float32 image
  ↓
face detection and landmark selection
  ↓
face/skin/eye/mouth/protected masks
  ↓
liquify handles from active face and params
  ↓
inverse MLS dense warp map
  ↓
single OpenCV remap + liquify mask blend
  ↓
refined skin mask on warped image
  ↓
guided-filter skin smoothing
  ↓
blemish soften
  ↓
Lab skin tone even
  ↓
eye bright / teeth white / brightness / soft contrast
  ↓
RGB float32 result
```

## 2. Face Detection

`face.py` currently uses a practical fallback chain:

1. MediaPipe Face Mesh when the package and runtime are available.
2. OpenCV Haar face detector.
3. Skin-region candidate fallback.
4. Heuristic centered fallback when explicitly allowed.

Detected Haar and MediaPipe boxes are expanded before creating synthetic or real landmark regions so cheeks, jaw, chin, and hairline-adjacent masks have enough context. `find_face` selects the requested `face_id` or the largest face.

## 3. Landmark and Mask Regions

Landmark index groups live in `engine/beauty_engine/landmark_indices.py`.

Current masks from `masks.py`:

| Mask | Source | Use |
|---|---|---|
| `face` | Face oval polygon, dilation, feather | Liquify blending and region bounds |
| `skin` | Face mask minus eyes/brows/mouth/nose/hairline approximation | Initial face skin mask |
| `eyes` | Eye polygons, dilation, feather | Eye bright and protection |
| `mouth` | Lip polygons, dilation, feather | Smile/teeth/mouth protection |
| `teeth` | Inner lip polygon | Teeth candidate area |
| `protected` | Eyes + brows + mouth + nose + hairline approximation | Reduces smoothing and shape edits |

All masks are `float32` in `0.0..1.0` and match the current processing image size.

## 4. Liquify

Liquify is implemented in `liquify.py` as handle-based inverse dense warp.

```text
source handles
  ↓
slider-adjusted target handles
  ↓
inverse MLS solve target -> source
  ↓
map_x/map_y float32
  ↓
cv2.remap(original, map_x, map_y)
  ↓
masked blend with original
```

Important current rules:

- All active face liquify sliders combine into one handle set.
- The image is remapped once per liquify call.
- Image border anchors and expanded face boundary anchors stabilize background.
- Protected anchors keep eyes, lips, nose tip, brows, and other non-target features stable when they are not the active slider target.
- A foldover probe computes Jacobian determinant on a reduced map. If unsafe values are detected, target displacement is progressively reduced.

Debug outputs when `debug_dir` is set:

```text
warp_grid.png
control_handles.png
liquify_mask.png
foldover_heatmap.png
```

### Slider Handle Behavior

| Slider | Current handle behavior |
|---|---|
| `face_slim` | Cheek, jaw, and face oval side points move toward face center with lower-face weighting |
| `jawline` | Lower jaw points move inward and slightly upward |
| `chin_length` | Chin points move vertically |
| `eye_enlarge` | Eye landmarks scale outward around each eye center |
| `nose_slim` | Nose wing and lower bridge points move toward bridge center |
| `smile` | Mouth corners and supporting lip points move up and slightly outward |

## 5. MLS Warp

`warp.py` implements:

- `identity_maps(shape)`
- `remap(image, map_x, map_y, interpolation=cv2.INTER_LINEAR)`
- `mls_similarity_maps(shape, source_handles, target_handles, max_grid_points=18000, alpha=1.0)`
- `jacobian_determinant(map_x, map_y)`

`mls_similarity_maps` evaluates similarity MLS on a sparse grid, upsamples the map to full processing size with cubic interpolation, clamps map coordinates into image bounds, and returns inverse sampling maps. The call convention is:

```python
map_x, map_y = mls_similarity_maps(shape, source_handles, target_handles)
```

Internally it solves target-to-source because `cv2.remap` expects each output pixel to sample from source coordinates.

## 6. Skin Retouch

Skin retouch is implemented in `smoothing.py`.

### Refined Skin Mask

`refined_skin_mask(image, masks)` combines:

1. Initial face skin mask.
2. Skin-color expansion learned from face skin pixels in Lab/YCrCb/HSV.
3. Connected-component filtering to reduce large background regions and tiny noise.
4. Protected-region subtraction.
5. Guided feathering against image luma.

This is a CPU heuristic, not semantic human parsing. It can include false positives on skin-colored backgrounds; debug output must be used while tuning.

### Smooth Skin

`smooth_skin` uses:

1. Guided-filter base extraction.
2. Stronger guided-filter smoothing on the base layer.
3. Detail reconstruction controlled by `texture_keep`.
4. Edge-protected mask blending.

### Blemish Soften

`soften_blemishes` detects red, dark, and high-contrast candidates inside the refined skin mask and blends toward a local median result with feathered strength.

### Skin Tone Even

`even_skin_tone` works in Lab:

- Smooths chroma channels.
- Applies a mild local L lift.
- Blends through a guided version of the refined skin mask.

## 7. Beauty Adjustments

`beauty.py` currently provides:

| Function | Behavior |
|---|---|
| `adjust_brightness` | Positive brightness lifts with luma-based shadow protection; negative brightness scales down |
| `adjust_soft_contrast` | Mild centered contrast factor |
| `brighten_eyes` | Uses eye mask plus low-saturation/high-value candidates |
| `whiten_teeth` | Uses teeth mask plus saturation/value heuristics and Lab tint reduction |

## 8. Debug Outputs

`process_image(..., debug_dir=...)` currently writes:

```text
landmarks.png            # from CLI process before pipeline
face_mask.png
skin_mask.png            # initial face skin mask
refined_skin_mask.png    # actual skin retouch mask
eye_mask.png
mouth_mask.png
warp_grid.png
control_handles.png
liquify_mask.png
foldover_heatmap.png
```

`debug_render_masks` returns landmarks, face mask, initial skin mask, and refined skin mask paths.

## 9. Determinism

CPU output should be deterministic for identical input image, parameters, face selection, and dependency versions. Floating-point and OpenCV implementation differences can still create tiny tolerance-level changes across platforms.

## 10. Known Limitations

- No current body pose, human parsing, body cage, body sliders, ARAP, or DensePose integration.
- GPU backends are diagnostic probes only.
- Refined skin mask is heuristic and can misclassify skin-colored background.
- Face detection is robust enough for the demo path but not equivalent to InsightFace/SCRFD.
- Landmark confidence and yaw/pitch validation are not yet fully modeled.
