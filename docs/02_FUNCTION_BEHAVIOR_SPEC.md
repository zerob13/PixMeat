# Function Behavior Specification

## 1. Application Launch

### Behavior

1. On launch, the app shows an empty editor state.
2. The app starts the local Python engine in the background.
3. The app calls `health` on the engine.
4. The app displays engine/backend diagnostics in the status bar.
5. The user can open an image through button, menu, or drag-and-drop.

### Empty State UI

```text
┌──────────────────────────────────────────────────────────┐
│ PixMeat                                                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│                  Drop a portrait image                   │
│                                                          │
│                     [Open Image]                         │
│                                                          │
│      Supported: JPG, PNG, WebP, TIFF                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ Engine: starting...                                      │
└──────────────────────────────────────────────────────────┘
```

### Acceptance Criteria

- App window appears within a normal desktop-app launch time.
- Engine status updates from `starting` to `ready` or `error`.
- User can open image after engine is ready.
- UI remains usable when engine starts slowly.

## 2. Open Image

### Triggers

- Click `Open Image`.
- Drag image into window.
- Use menu item `File > Open`.

### Behavior

1. Validate file extension.
2. Send `load_image` request to engine.
3. Engine reads metadata and creates preview asset.
4. Engine detects faces.
5. UI displays image preview.
6. UI displays face boxes when faces are detected.
7. Largest face becomes active by default.

### Failure Behavior

| Case | UI Message | Engine Behavior |
|---|---|---|
| Unsupported file | `Unsupported image format` | Return `unsupported_format` |
| File read failure | `Cannot open image` | Return `read_error` |
| Face analysis failure | `Face analysis failed` | Allow basic view/export without face edits |
| Zero faces | `No face detected. Beauty sliders are disabled.` | Return `faces: []` |

### Acceptance Criteria

- Valid image opens and shows preview.
- Invalid image shows clear error.
- No-face images can still be viewed and exported unchanged.
- Face-dependent sliders disable when no active face exists.

## 3. Active Face Selection

### Behavior

1. UI draws rectangles over detected faces when `Show Faces` is active.
2. Clicking a rectangle selects the active face.
3. Active face rectangle uses a stronger outline.
4. Parameter changes apply to active face.
5. Face selection persists while the current image remains open.

### Edge Cases

| Case | Behavior |
|---|---|
| Multiple faces overlap | Click selects topmost/largest overlapping face |
| Active face becomes invalid after reload | Default to largest face |
| No face selected | Select largest face if available |

### Acceptance Criteria

- Active face can be switched in multi-face image.
- Slider edits visually affect selected face.
- Active face id is included in preview/export requests.

## 4. Slider Interaction

### General Behavior

1. Slider value changes locally in UI immediately.
2. Slider drag emits debounced preview requests.
3. Slider release emits high-quality preview request.
4. A newer request cancels or supersedes older preview requests.
5. The preview displays a subtle processing indicator during render.
6. The latest completed request updates the preview.

### Debounce Rules

| Event | Behavior |
|---|---|
| Slider drag starts | Mark editor state dirty |
| Slider moves | Debounce preview request around 80-150 ms |
| Slider release | Send `preview_quality: standard` request immediately |
| Multiple sliders move quickly | Merge into latest params |

### Acceptance Criteria

- Slider movement feels responsive.
- Out-of-order engine responses cannot overwrite newer previews.
- Reset and preset application follow the same preview rules.

## 5. Body Group

### 5.1 Body Shape, Waist, Arms

#### Range

`-100 to 100`, default `0`.

#### Behavior

- Sliders are centered at `0`; negative values widen/fatten the target region and positive values slim/narrow it.
- Body shape and waist use torso-side MLS handles.
- Arm shape uses side/arm handles and an Analysis V2 person/body mask when available.
- At value `0`, this module returns the input unchanged.

#### Acceptance Criteria

- Positive values visibly slim the corresponding body region.
- Negative values visibly widen the corresponding body region.
- Face and upper-head areas remain stable during body edits.
- Background distortion is limited by the body/person blend mask.

## 6. Liquify Group

### 6.1 Face Shape

#### Range

`-100 to 100`, default `0`.

#### Behavior

- Positive values move cheek and jaw contour points toward the vertical face center line.
- Negative values move cheek and jaw contour points away from the vertical face center line.
- Movement strength depends on face width.
- Upper cheek movement is milder than lower cheek movement.
- Image and face boundary anchors protect ears, hair, neck, and background.
- Current implementation builds source/target handles and solves one inverse MLS dense map before a single OpenCV remap.

#### Visual Expectation

- At 20-35, effect is natural for portrait retouching.
- At 50+, effect is visibly stylized.
- At 100, output remains bounded and avoids face collapse.

#### Acceptance Criteria

- At value 0, output equals input for this module.
- At value 30, cheeks slim visibly.
- At value -30, cheeks widen visibly without tearing.
- Jaw contour remains continuous.
- Background distortion remains contained by face mask blend.

### 6.2 Jawline

#### Range

`-100 to 100`, default `0`.

#### Behavior

- Positive values move lower jawline points inward and slightly upward.
- Negative values move lower jawline points outward and slightly downward.
- Chin center remains stable unless `chin_length` changes.
- The algorithm emphasizes a cleaner jaw contour through geometric warp only.

#### Acceptance Criteria

- Jaw shape becomes cleaner at 30 and fuller at -30.
- Chin position remains close to original when `chin_length = 0`.
- Mouth and nose remain stable.

### 6.3 Chin Length

#### Range

`-50 to 50`, default `0`.

#### Behavior

- Positive values lengthen chin downward along face vertical axis.
- Negative values shorten chin upward.
- Movement is strongest at chin center and fades toward jaw corners.

#### Acceptance Criteria

- Chin length changes without moving mouth significantly.
- Face oval mask expands/contracts enough to blend shape changes.

### 6.4 Eye Size

#### Range

`-100 to 100`, default `0`.

#### Behavior

- Positive values enlarge both eyes around their respective centers.
- Negative values shrink both eyes around their respective centers.
- Upper/lower eyelid points and eye corner points are transformed through target handles.
- Eyebrows remain mostly stable.
- Iris and eye white follow the local warp.

#### Acceptance Criteria

- At 20, eyes become subtly larger.
- At -20, eyes become subtly smaller.
- At 50, eyes enlarge clearly while face texture remains continuous.
- Eye centers remain stable.

### 6.5 Nose Width

#### Range

`-100 to 100`, default `0`.

#### Behavior

- Positive values move nose wing points toward nose bridge center.
- Negative values move nose wing points away from nose bridge center.
- Nostrils remain visible.
- Mouth and cheeks stay stable.

#### Acceptance Criteria

- Nose width reduces at 30.
- Nose width increases at -30.
- Nostrils avoid severe collapse at high values.
- Symmetry is preserved for frontal faces.

### 6.6 Smile

#### Range

`-100 to 100`, default `0`.

#### Behavior

- Positive values move mouth corners upward and slightly outward.
- Negative values move mouth corners downward and slightly inward.
- Upper lip and lower lip receive smooth supporting offsets.
- Nasolabial region receives very mild deformation.

#### Acceptance Criteria

- Mouth corners lift at 30.
- Mouth corners lower at -30.
- Teeth/mouth interior distort mildly and plausibly.
- Nose and chin remain stable.

## 7. Skin Group

### 6.1 Skin Smooth

#### Range

`0-100`, default `0`.

#### Behavior

- Smooths low-frequency skin color and tone.
- Preserves high-frequency detail according to `texture_keep`.
- Applies through a refined skin mask built from the face skin mask plus conservative skin-color expansion.
- Excludes eyes, eyebrows, lips, nostrils, teeth, and hair approximation.
- Current implementation uses guided filtering, base/detail reconstruction, edge protection, and texture restoration.

#### Acceptance Criteria

- At 0, skin module has no effect.
- At 30, uneven skin tone softens.
- At 70, skin becomes visibly smoother while main facial edges stay protected.

### 6.2 Texture Keep

#### Range

`0-100`, default `70`.

#### Behavior

- Controls how much high-frequency detail is added back after smoothing.
- Higher values preserve pores and natural texture.
- Lower values create stronger smoothing.

#### Acceptance Criteria

- Increasing texture keep restores fine skin detail.
- At 100, smoothing mainly affects color/tone and preserves texture.

### 6.3 Blemish Soften

#### Range

`0-100`, default `0`.

#### Behavior

- Detects small high-contrast, red, or dark spots within the refined skin mask.
- Applies local median-blend spot softening.
- Ignores moles and strong facial features when confidence is low.

#### V1 Implementation

- Implemented as conservative local smoothing around detected red/dark/high-contrast spots.
- Spot strength is feathered and bounded by the refined skin mask.
- Refined skin mask debug output is available in developer mode.

#### Acceptance Criteria

- Small blemishes soften at 40.
- Eyes, eyebrows, lips, nostrils remain unaffected.
- False positives are limited through mask protection.

### 6.4 Skin Tone Even

#### Range

`0-100`, default `0`.

#### Behavior

- Operates in Lab or HSV color space.
- Smooths skin chroma variation while preserving luminance detail.
- Uses refined skin mask and edge-aware blending.

#### Acceptance Criteria

- Redness and uneven skin patches become milder.
- Lips and eye regions preserve original color.

## 8. Beauty Group

### 7.1 Brightness

#### Range

`-50 to 50`, default `0`.

#### Behavior

- Applies mild brightness adjustment to portrait/skin region.
- Uses a soft curve with shadow protection for positive brightness.
- Protects highlights with rolloff.

#### Acceptance Criteria

- Positive values brighten skin naturally.
- Negative values darken without crushing shadows excessively.

### 7.2 Eye Bright

#### Range

`0-100`, default `0`.

#### Behavior

- Identifies eye regions from landmarks.
- Brightens eye white and adds mild local contrast.
- Avoids expanding into eyelids and surrounding skin.

#### Acceptance Criteria

- At 30, eyes look clearer.
- Eyelids and skin retain stable color.

### 7.3 Teeth White

#### Range

`0-100`, default `0`.

#### Behavior

- Identifies likely teeth region inside mouth landmarks.
- Reduces yellow saturation and lifts luminance.
- Applies only to pixels that match teeth color heuristics.

#### Acceptance Criteria

- Teeth whiten at 30 when visible.
- Lips retain red/pink color.
- Closed-mouth images produce minimal changes.

### 7.4 Soft Contrast

#### Range

`-50 to 50`, default `0`.

#### Behavior

- Applies mild S-curve or reverse S-curve.
- Operates globally or on portrait mask according to setting.
- Maintains preview/export consistency.

#### Acceptance Criteria

- Positive values add portrait pop.
- Negative values create softer look.

## 9. Presets

### Built-In Presets

| Preset | Values |
|---|---|
| Natural | Small smoothing, mild tone even, tiny eye brighten |
| Clean Portrait | Moderate smoothing, medium tone even, mild liquify |
| Soft Beauty | Stronger smoothing, high texture keep, mild brightening |
| Reset | All sliders back to defaults |

### User Presets

1. User can save current parameters as a preset.
2. Preset stores parameter values only.
3. Preset is stored in local app data.
4. Applying preset triggers preview render.

### Acceptance Criteria

- Built-in presets are available after first launch.
- User preset persists across app restarts.
- Reset restores default values and preview.

## 10. Before / After / Split View

### Modes

| Mode | Behavior |
|---|---|
| Before | Shows original preview |
| After | Shows processed preview |
| Split | Left side original, right side processed |
| Hold-to-compare | Press and hold shortcut to temporarily show original |

### Acceptance Criteria

- Split divider can be dragged.
- Before/after toggles without recomputing.
- Zoom/pan state remains stable across modes.

## 11. Export

### Behavior

1. User clicks `Export`.
2. App asks for output path and format.
3. Engine processes original-resolution image.
4. Progress is displayed.
5. User can cancel export.
6. Final file is written to selected path.

### Export Options

| Option | Values |
|---|---|
| Format | JPEG, PNG, TIFF optional |
| JPEG quality | 70-100, default 92 |
| Keep metadata | Basic V1 option |
| Open folder after export | Checkbox |

### Acceptance Criteria

- Exported file opens in normal image viewers.
- Export respects current active parameters.
- Export uses full-resolution source.
- Cancel stops job and cleans temp output.

## 12. Settings

### Settings Items

| Setting | Default | Behavior |
|---|---|---|
| Preferred backend | Auto | Auto/CUDA/MPS/OpenCV CUDA/CPU diagnostics; CPU processing in current build |
| Preview max side | 1600 | 800/1200/1600/2000 |
| Show face boxes | On | Toggle overlay |
| Cache size limit | 2 GB | Clear old cache |
| Privacy mode | Off | Redact full paths in logs |

### Acceptance Criteria

- Settings persist across restarts.
- Backend preference triggers engine re-check.
- Cache can be cleared manually.
