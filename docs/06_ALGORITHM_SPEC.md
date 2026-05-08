# Algorithm Specification

## 1. Algorithm Goals

The engine should produce natural portrait edits with deterministic, parameter-controlled behavior.

Core principles:

1. Use face landmarks as the control structure.
2. Use masks to restrict edits to intended regions.
3. Preserve identity and texture.
4. Blend edits softly into original image.
5. Keep preview and export semantics consistent.

## 2. Overall Pipeline

```text
image_rgb
  ↓
face detection + landmarks
  ↓
region masks
  ↓
liquify warp
  ↓
skin smoothing
  ↓
skin tone even
  ↓
blemish soften
  ↓
eye brighten
  ↓
teeth whiten
  ↓
brightness / contrast
  ↓
result_rgb
```

## 3. Face Landmarks

### Landmark Provider

Use MediaPipe Face Landmarker or Face Mesh.

### Required Landmark Regions

| Region | Use |
|---|---|
| Face oval | Face mask, jaw/chin controls |
| Left eye | Eye enlarge, eye mask |
| Right eye | Eye enlarge, eye mask |
| Eyebrows | Mask exclusion |
| Nose | Nose slim controls, nostril protection |
| Lips | Smile, mouth mask, teeth candidate region |
| Cheeks | Face slim controls |

### Suggested MediaPipe Index Groups

Keep these constants in `landmark_indices.py` and tune during implementation.

```python
FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356,
    454, 323, 361, 288, 397, 365, 379, 378,
    400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21,
    54, 103, 67, 109
]

LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

LEFT_EYEBROW = [70, 63, 105, 66, 107, 46, 53, 52, 65, 55]
RIGHT_EYEBROW = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]

OUTER_LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
INNER_LIPS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]

NOSE_BRIDGE = [6, 197, 195, 5, 4, 1]
NOSE_LEFT = [98, 97, 2, 326, 327]
NOSE_RIGHT = [327, 326, 2, 97, 98]
NOSE_TIP = [1, 2, 4, 5]

CHIN = [152, 175, 199, 200, 18, 313, 406]
LEFT_JAW = [234, 93, 132, 58, 172, 136, 150, 149, 176, 148]
RIGHT_JAW = [454, 323, 361, 288, 397, 365, 379, 378, 400, 377]
```

The implementation should include a visual debug mode to verify index groups.

## 4. Coordinate Systems

### Normalized Coordinates

MediaPipe returns landmarks in normalized image coordinates. Store normalized coordinates in session metadata.

### Pixel Coordinates

For each processing size:

```python
def to_pixel(points_norm, width, height):
    points = points_norm.copy()
    points[:, 0] *= width
    points[:, 1] *= height
    return points
```

### Face Local Coordinate System

For liquify, define face-local axes:

```text
center_x = midpoint between left/right face bounds
center_y = midpoint between forehead/chin bounds
face_width = right_bound - left_bound
face_height = chin_y - forehead_y
vertical_axis = line from forehead center to chin
horizontal_axis = perpendicular to vertical axis
```

Use local axes for robust behavior on slightly tilted faces.

## 5. Mask Generation

### 5.1 Face Mask

1. Get `FACE_OVAL` points.
2. Create polygon mask.
3. Expand mask by a small radius proportional to face size.
4. Feather mask edges.

```python
def build_face_mask(shape, landmarks):
    polygon = landmarks[FACE_OVAL][:, :2]
    mask = fill_polygon(shape, polygon)
    mask = dilate(mask, radius=face_size * 0.03)
    mask = gaussian_blur(mask, sigma=face_size * 0.015)
    return clamp01(mask)
```

### 5.2 Skin Mask

Start from face mask, then subtract protected regions:

- Eyes
- Eyebrows
- Lips
- Nostrils
- Hairline approximation

```text
skin_mask = face_mask
  - eye_masks expanded
  - eyebrow_masks expanded
  - lip_mask expanded
  - nostril_mask
  - upper forehead reduction
```

### 5.3 Eye Mask

Build from left/right eye polygons. Expand lightly and feather.

### 5.4 Mouth and Teeth Candidate Mask

Mouth mask is built from inner/outer lips. Teeth candidate pixels are selected inside inner mouth region using color heuristics:

```text
teeth_candidate = mouth_inner_mask
  AND luminance > local threshold
  AND saturation < local threshold
  AND hue/yellow score within range
```

### 5.5 Debug Masks

Developer mode can write:

```text
skin_mask.png
face_mask.png
eye_mask.png
mouth_mask.png
teeth_candidate_mask.png
landmark_overlay.png
```

## 6. Liquify Algorithm

## 6.1 Design

Liquify uses parameter-driven landmark offsets and a dense backward warp map.

```text
landmarks
  ↓
control points
  ↓
slider-specific offsets
  ↓
target control points
  ↓
warp map
  ↓
remap image
  ↓
blend with face mask
```

## 6.2 Control Points

Control points include:

1. Face oval landmarks.
2. Eye landmarks.
3. Nose landmarks.
4. Lip landmarks.
5. Cheek support points.
6. Boundary anchors around face region.
7. Image/crop boundary anchors.

Boundary anchors keep non-face areas stable.

```python
def build_control_points(landmarks, image_shape):
    points = []
    points.extend(region_points(FACE_OVAL))
    points.extend(region_points(LEFT_EYE))
    points.extend(region_points(RIGHT_EYE))
    points.extend(region_points(OUTER_LIPS))
    points.extend(region_points(NOSE_BRIDGE))
    points.extend(make_boundary_anchors(image_shape, face_bbox))
    return np.array(points, dtype=np.float32)
```

## 6.3 Warp Methods

### V1 CPU Method

Use piecewise affine warp through Delaunay triangulation.

Steps:

1. Compute Delaunay triangles over source control points.
2. For each triangle, compute affine transform from source to target.
3. Render output triangle from source image.
4. Create final warped image.
5. Blend with face mask.

### V1 Torch Backend Method

Use a dense flow field and `grid_sample` style sampling.

Steps:

1. Create identity grid.
2. Add smooth displacement fields from slider functions.
3. Convert to normalized grid coordinates.
4. Sample image tensor.
5. Blend with mask.

### Future Native Method

Implement CUDA and Metal compute kernels for dense remap.

## 6.4 Slider Offset Functions

### Face Slim

```python
def apply_face_slim(points, landmarks, strength):
    center_x = face_center_x(landmarks)
    for idx in LEFT_JAW + RIGHT_JAW + cheek_indices():
        p = points[idx]
        side = np.sign(p.x - center_x)
        weight = jaw_cheek_weight(idx)
        p.x -= side * strength * weight * face_width * 0.08
    return points
```

Recommended scale:

```text
max displacement ≈ 8% of face width at strength 1.0
```

### Jawline

```python
def apply_jawline(points, landmarks, strength):
    center_x = face_center_x(landmarks)
    for idx in lower_jaw_indices():
        p = points[idx]
        side = np.sign(p.x - center_x)
        p.x -= side * strength * jaw_weight(idx) * face_width * 0.05
        p.y -= strength * lift_weight(idx) * face_height * 0.025
    return points
```

### Chin Length

```python
def apply_chin_length(points, landmarks, strength):
    for idx in chin_indices():
        p = points[idx]
        p.y += strength * chin_weight(idx) * face_height * 0.06
    return points
```

### Eye Enlarge

Eye enlarge is local radial warp.

```python
def eye_enlarge_displacement(grid, eye_center, eye_radius, strength):
    d = grid - eye_center
    r = norm(d)
    falloff = exp(-(r / eye_radius) ** 2)
    scale = strength * 0.18 * falloff
    displacement = -d * scale
    return displacement
```

For backward mapping, displacement direction should be inverted according to sampling convention.

### Nose Slim

```python
def apply_nose_slim(points, landmarks, strength):
    nose_center_x = mean_x(NOSE_BRIDGE)
    for idx in nose_wing_indices():
        p = points[idx]
        side = np.sign(p.x - nose_center_x)
        p.x -= side * strength * face_width * 0.025
    return points
```

### Smile

```python
def apply_smile(points, landmarks, strength):
    for idx in mouth_corner_indices():
        p = points[idx]
        p.y -= strength * face_height * 0.025
        p.x += side(idx) * strength * face_width * 0.01
    return points
```

## 6.5 Liquify Blending

Blend warped result with original through face mask.

```python
result = original * (1.0 - face_mask) + warped * face_mask
```

For strong face slim, expand face mask around cheeks and jaw to cover moved pixels.

## 6.6 Liquify Safety Clamps

| Parameter | Clamp |
|---|---|
| Face slim | max 8% face width displacement |
| Jawline | max 5% face width, 2.5% face height lift |
| Chin | max 6% face height |
| Eye enlarge | max 18% local radial scale |
| Nose slim | max 2.5% face width |
| Smile | max 2.5% face height lift |

## 7. Skin Smoothing Algorithm

## 7.1 Frequency Separation

```text
low = edge_preserving_blur(image)
high = image - low
smoothed_low = stronger_blur(low or image)
result = smoothed_low + high * texture_keep
```

### CPU Implementation

1. Use bilateral filter or guided filter approximation.
2. Use Gaussian blur for low-frequency separation.
3. Reconstruct with high-frequency detail.
4. Apply through skin mask.

```python
def smooth_skin(image, skin_mask, smooth, texture_keep):
    low = bilateral_filter(image, radius, sigma_color, sigma_space)
    high = image - low
    smooth_low = gaussian_blur(low, sigma)
    reconstructed = smooth_low + high * texture_keep
    amount = smooth
    return image * (1 - skin_mask * amount) + reconstructed * (skin_mask * amount)
```

## 7.2 Texture Keep Behavior

```text
texture_keep = 1.0 → original texture retained
texture_keep = 0.7 → natural smoothing
texture_keep = 0.3 → strong beauty smoothing
texture_keep = 0.0 → plastic smoothing risk
```

## 7.3 Edge Protection

Before smoothing, reduce mask around edges:

- Eye boundaries
- Lip boundaries
- Nose nostrils
- Eyebrows
- Hairline

Use distance transform to soften mask transitions.

## 8. Blemish Soften Algorithm

## 8.1 V1 Conservative Detection

Within skin mask:

1. Convert image to Lab/HSV.
2. Estimate local median or local blurred color.
3. Compute residual map.
4. Detect small dark/red spots.
5. Remove regions above max area threshold.
6. Apply local blend toward surrounding skin tone.

```python
residual = abs(image_lab - local_median_lab)
spot_score = weighted_residual(residual, red_channel_bias=True)
spot_mask = threshold(spot_score) & skin_mask
spot_mask = remove_large_components(spot_mask)
spot_mask = feather(spot_mask)
```

## 8.2 Correction

```python
corrected = local_blur_or_inpaint(image, spot_mask)
result = blend(image, corrected, spot_mask * blemish_soften)
```

## 8.3 Safety

- Maximum spot radius proportional to face size.
- Exclude feature masks.
- Debug output for tuning.

## 9. Skin Tone Even Algorithm

## 9.1 Lab Chroma Smoothing

1. Convert RGB to Lab.
2. Smooth `a` and `b` channels inside skin mask.
3. Preserve `L` channel details.
4. Blend according to `skin_tone_even`.

```python
lab = rgb_to_lab(image)
a_smooth = edge_blur(lab.a)
b_smooth = edge_blur(lab.b)
lab_even = lab.copy()
lab_even.a = mix(lab.a, a_smooth, amount)
lab_even.b = mix(lab.b, b_smooth, amount)
result = lab_to_rgb(lab_even)
```

## 10. Eye Bright Algorithm

1. Build eye mask.
2. Estimate eye white candidate pixels using low saturation + high brightness.
3. Brighten candidate pixels with highlight rolloff.
4. Add mild local contrast to iris region only when safe.

```python
candidate = eye_mask & (saturation < s_thresh) & (value > v_thresh)
amount = eye_bright
result = lift_luminance(image, candidate, amount)
```

## 11. Teeth White Algorithm

1. Build inner mouth mask.
2. Select candidate pixels using brightness/saturation/yellow score.
3. Reduce yellow tint.
4. Lift luminance mildly.
5. Feather mask.

```python
teeth = mouth_inner & (value > 0.35) & (saturation < 0.6)
result = reduce_yellow(image, teeth, amount)
result = lift_luminance(result, teeth, amount * 0.5)
```

## 12. Brightness and Soft Contrast

### Brightness

Use curve-based adjustment:

```python
def adjust_brightness(x, amount):
    if amount >= 0:
        return x + (1 - x) * amount * 0.35
    return x * (1 + amount * 0.35)
```

### Soft Contrast

Use mild S-curve:

```python
def soft_contrast_curve(x, amount):
    centered = x - 0.5
    factor = 1.0 + amount * 0.4
    return clamp01(0.5 + centered * factor)
```

## 13. Preview Scaling

For preview, landmarks detected on preview image are acceptable. For export, use original-size landmarks or scale normalized landmarks to original dimensions.

Recommended:

1. Detect landmarks on preview for responsiveness.
2. Store normalized landmarks.
3. Reuse normalized landmarks for export.
4. Re-detect on original only when export quality debug flag is enabled.

## 14. Determinism

Given identical input image, backend, and parameters, output should be deterministic within floating-point tolerance.

Golden-image tests should allow small tolerance between CPU/CUDA/MPS outputs.

## 15. Developer Debug Tools

Add a developer panel or CLI flags:

```bash
python -m beauty_engine.cli process input.jpg output.jpg \
  --face-slim 30 \
  --skin-smooth 40 \
  --debug-dir debug_out
```

Debug output:

```text
landmarks.png
face_mask.png
skin_mask.png
warp_grid.png
before_after.png
result.png
```

