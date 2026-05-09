# UI / UX Specification

## 1. Design Principles

1. Single-purpose editor.
2. Slider-first interaction.
3. Fast preview before perfect export.
4. Clear before/after comparison.
5. Minimal panels and minimal navigation.
6. Local processing status always visible.

## 2. Main Window Layout

```text
┌───────────────────────────────────────────────────────────────────────┐
│ PixMeat                                                   macOS/Win   │
├───────────────────────────────────────────────────────────────────────┤
│ File  Edit  View  Presets  Help                                      │
├───────────────┬───────────────────────────────────────┬───────────────┤
│ Left Toolbar  │ Canvas                                │ Right Panel   │
│               │                                       │               │
│ [Open]        │                                       │ Face          │
│ [Compare]     │            Image Preview              │  Face #1 ▼    │
│ [Fit]         │                                       │               │
│ [Zoom]        │        Before | Split | After          │ Body          │
│               │                                       │  Body Shape   │
│               │                                       │  Waist        │
│               │                                       │  Arms         │
│               │                                       │               │
│               │                                       │ Liquify       │
│               │                                       │  Face Shape   │
│               │                                       │  Jawline      │
│               │                                       │  Chin         │
│               │                                       │  Eye Size     │
│               │                                       │  Nose Width   │
│               │                                       │  Smile        │
│               │                                       │               │
│               │                                       │ Skin          │
│               │                                       │  Smooth       │
│               │                                       │  Texture      │
│               │                                       │  Blemish      │
│               │                                       │  Tone Even    │
│               │                                       │               │
│               │                                       │ Beauty        │
│               │                                       │  Brightness   │
│               │                                       │  Eye Bright   │
│               │                                       │  Teeth White  │
│               │                                       │  Contrast     │
├───────────────┴───────────────────────────────────────┴───────────────┤
│ Engine: Ready · Backend: CPU · Preview: 1600px · Dirty                │
└───────────────────────────────────────────────────────────────────────┘
```

## 3. Empty State

```text
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                       Drop a portrait image                           │
│                                                                       │
│                          [Open Image]                                 │
│                                                                       │
│                  JPG · PNG · WebP · TIFF                              │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## 4. Right Panel Structure

### Face Section

```text
Face
┌───────────────────────────────┐
│ Active Face: Face #1      ▼   │
│ Show face boxes          [✓]  │
└───────────────────────────────┘
```

### Body Section

```text
Body                            Reset
Body Shape  -100 ━━━━━●━━━━━━━ 100
Waist       -100 ━━━━━●━━━━━━━ 100
Arms        -100 ━━━━━●━━━━━━━ 100
```

### Liquify Section

```text
Liquify                         Reset
Face Shape  -100 ━━━━━●━━━━━━━ 100
Jawline     -100 ━━━━━●━━━━━━━ 100
Chin         -50 ━━━━━●━━━━━━━  50
Eye Size    -100 ━━━━━●━━━━━━━ 100
Nose Width  -100 ━━━━━●━━━━━━━ 100
Smile       -100 ━━━━━●━━━━━━━ 100
```

### Skin Section

```text
Skin                             Reset
Skin Smooth    0 ━━━━━━━━━━━━━ 100
Texture Keep   0 ━━━━━━━●━━━━━ 100
Blemish        0 ━━━━━━━━━━━━━ 100
Tone Even      0 ━━━━━━━━━━━━━ 100
```

### Beauty Section

```text
Beauty                           Reset
Brightness   -50 ━━━━━●━━━━━━━  50
Eye Bright     0 ━━━━━━━━━━━━━ 100
Teeth White    0 ━━━━━━━━━━━━━ 100
Soft Contrast -50 ━━━━━●━━━━━━━  50
```

## 5. Top Toolbar

```text
[Open] [Save Preset] [Before] [Split] [After] [Fit] [100%] [Export]
```

### Button Behavior

| Button | Behavior |
|---|---|
| Open | Show file picker |
| Save Preset | Save current params as preset |
| Before | Show original preview |
| Split | Show draggable split comparison |
| After | Show processed preview |
| Fit | Fit image to viewport |
| 100% | Show actual preview pixels |
| Export | Export original-resolution result |

## 6. Canvas Behavior

### Pan and Zoom

| Action | Behavior |
|---|---|
| Mouse wheel | Zoom around cursor |
| Trackpad pinch | Zoom around center/cursor |
| Space + drag | Pan |
| Double click | Toggle fit/100% |
| Cmd/Ctrl + 0 | Fit |
| Cmd/Ctrl + 1 | 100% |

### Face Boxes

- Face boxes appear over the image when `Show face boxes` is enabled.
- Active face box uses highlighted border.
- Inactive face boxes use lighter border.
- Clicking a face box changes active face.

## 7. Preview State Indicators

| State | UI Indicator |
|---|---|
| Engine starting | Status bar: `Engine: starting...` |
| Engine ready | Status bar: `Engine: ready` |
| Face analysis running | Spinner near status bar |
| Preview rendering | Subtle overlay spinner |
| Export running | Modal progress bar |
| Error | Inline message and status bar warning |

## 8. Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Cmd/Ctrl + O | Open image |
| Cmd/Ctrl + S | Export |
| Cmd/Ctrl + R | Reset all sliders |
| Cmd/Ctrl + 0 | Fit to screen |
| Cmd/Ctrl + 1 | 100% zoom |
| Space + drag | Pan canvas |
| `B` | Toggle before/after |
| `S` | Toggle split view |
| `F` | Toggle face boxes |
| Esc | Cancel current export or close modal |

## 9. Slider Interaction Details

### Normal Slider

1. Display label.
2. Display numeric value.
3. Display draggable track.
4. Support mouse, keyboard, and trackpad.
5. Support direct numeric entry after clicking value.

### Slider Drag Behavior

```text
User drags slider
  ↓
UI updates value immediately
  ↓
Preview request debounced
  ↓
Engine returns processed preview
  ↓
Canvas updates after latest request id matches
```

### Slider Value Editing

- Clicking numeric value opens inline input.
- Enter commits value.
- Esc cancels editing.
- Values are clamped to valid range.

## 10. Preset UX

```text
Presets ▼
┌────────────────────┐
│ Natural            │
│ Clean Portrait     │
│ Soft Beauty        │
│ ------------------ │
│ Save Current...    │
│ Manage Presets...  │
└────────────────────┘
```

### Behavior

- Applying preset updates all sliders.
- Applying preset triggers preview render.
- Saved presets appear below built-ins.
- User presets can be renamed and deleted.

## 11. Export Dialog

```text
┌─────────────────────────────────────────────┐
│ Export                                      │
├─────────────────────────────────────────────┤
│ File name      [portrait_retouched.jpg]     │
│ Format         [JPEG ▼]                     │
│ Quality        92 ━━━━━━━━━━━━━ 100         │
│ Keep metadata  [✓]                          │
│ Open folder    [✓]                          │
│                                             │
│                 [Cancel] [Export]           │
└─────────────────────────────────────────────┘
```

### Export Progress

```text
┌─────────────────────────────────────────────┐
│ Exporting full-resolution image             │
│ ███████████████░░░░░░░░ 64%                 │
│ Backend: CPU                                │
│                                             │
│                         [Cancel]            │
└─────────────────────────────────────────────┘
```

## 12. Error UX

### Error Toast Pattern

```text
┌─────────────────────────────────────────────┐
│ Image analysis failed                       │
│ Face-dependent controls are disabled.        │
└─────────────────────────────────────────────┘
```

### Error Severity

| Severity | Behavior |
|---|---|
| Info | Status bar only |
| Warning | Toast + status bar |
| Error | Toast + panel message |
| Fatal | Modal with restart engine action |

## 13. Settings Screen

```text
┌─────────────────────────────────────────────┐
│ Settings                                    │
├─────────────────────────────────────────────┤
│ Performance                                 │
│ Preferred backend       [Auto ▼]            │
│ Preview max side        [1600 ▼]            │
│ Cache limit             [2 GB ▼]            │
│                                             │
│ Privacy                                     │
│ Redact paths in logs    [ ]                 │
│ Clear cache             [Clear]             │
│                                             │
│ Diagnostics                                 │
│ Engine status           Ready               │
│ Active backend          CPU/CUDA/MPS/OpenCV │
│ Python engine version   x.y.z               │
└─────────────────────────────────────────────┘
```

## 14. Responsive Behavior

### Minimum Window Size

- 1100 x 700 px recommended.
- At narrow widths, left toolbar collapses into icons.
- Right panel remains scrollable.

### High-DPI

- Use CSS pixel scaling for UI.
- Canvas draws image with device pixel ratio awareness.
- Avoid blurry preview on Retina/HiDPI.

## 15. Accessibility

1. Sliders support keyboard arrow keys.
2. Buttons have accessible labels.
3. Focus ring is visible.
4. Text contrast meets normal desktop expectations.
5. Numeric slider value is readable and editable.

## 16. Current UI Status

The current app implements the main editor surface, toolbar actions, face selection, slider panel, presets, settings, preview rendering, compare modes, and export path. Advanced debug layer toggles are not yet exposed in the renderer; debug artifacts are generated through engine CLI/API developer paths.
