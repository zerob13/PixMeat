# Analysis V2

Analysis V2 is the engine's model-backed, debuggable analysis pipeline. It keeps the existing retouch pipeline working while replacing threshold-only body and skin analysis with structured face, person, parsing, skin, and region outputs. Legacy skin/background face guesses are not part of the V2 fallback path.

## Configuration

Enable V2 through JSON-RPC payloads or environment variables:

```json
{
  "analysis": {
    "version": "v2",
    "debug": true,
    "device": "auto",
    "model_paths": {
      "face_detector": "/models/scrfd.onnx",
      "face_landmarker": "/models/face_landmarker.task",
      "person_segmentation": "/models/selfie_segmenter.task",
      "human_parsing": "/models/schp.onnx"
    }
  }
}
```

Supported devices are `auto`, `cpu`, `cuda`, and `mps`. CUDA is preferred for ONNX Runtime when available on Windows. MPS is reserved for future PyTorch model adapters on macOS. Every model slot falls back to CPU-safe behavior when a backend or model is unavailable.

Environment variables:

- `PIXMEAT_ANALYSIS_VERSION=v2`
- `PIXMEAT_ANALYSIS_DEBUG=true`
- `PIXMEAT_ANALYSIS_DEBUG_DIR=/path/to/debug`
- `PIXMEAT_ANALYSIS_DEVICE=auto|cpu|cuda|mps`
- `PIXMEAT_MODEL_DIR=/path/to/local/models`
- `PIXMEAT_FACE_DETECTOR_MODEL=/path/to/model`
- `PIXMEAT_FACE_LANDMARKER_MODEL=/path/to/model`
- `PIXMEAT_PERSON_SEGMENTATION_MODEL=/path/to/model`
- `PIXMEAT_HUMAN_PARSING_MODEL=/path/to/model`

No runtime network downloads are performed. Model files must already exist locally or in packaged app resources.

## Pipeline

`AnalysisV2.analyze(image_bgr)` accepts a BGR `uint8` image and returns an `AnalysisResult`. All coordinates outside model wrappers are stored in original image pixels.

Stages:

1. Validate BGR input and record scale metadata.
2. Detect faces through configured model-backed slots or the safe classic MediaPipe/eye-pair/Haar detector chain.
3. Expand face boxes before crop landmark inference and map crop landmarks back to original pixels.
4. Build a person mask through a configured segmentation model or geometric fallback.
5. Build human parsing labels through a configured parser or coarse person/face geometry.
6. Build skin masks from semantic skin/face/neck/arm labels, refine existing candidates with color checks, suppress with person mask, and exclude protected facial/hair/clothing regions.
7. Build downstream body and face region masks.
8. Export debug overlays when enabled.

The current CPU color skin checks are only a refinement of semantic skin candidates. They are not used as the body parser, primary body region source, or standalone skin fallback in V2.

## Output Schema

`AnalysisResult.to_json()` contains:

- `image_size`: `[width, height]`
- `faces`: face id, bbox, expanded bbox, score, confidence, source, landmark count, quality hints
- `selected_face_id`: primary face id
- `persons`: person id, bbox, confidence, source
- `selected_person_id`: primary person id
- `masks`: compact summaries for person, parsing, and skin masks
- `regions`: region bbox, confidence, source, and mask summary
- `confidence`: face, landmark, person segmentation, human parsing, skin mask, and overall scores
- `debug`: sources, timings, scale factors, and debug path
- `model_backends`: backend/provider/model path/availability diagnostics per model slot

In memory, masks and regions keep `float32` NumPy arrays in `[0, 1]`.

## Degraded Behavior

Missing or unsupported model paths do not crash analysis.

- Face landmarks: local MediaPipe Face Landmarker `.task` when configured; otherwise synthetic landmark mapping is used only after a real classic detector candidate exists.
- Face detection: configured SCRFD/RetinaFace ONNX path is recorded, but a concrete adapter is still future work; safe classic MediaPipe/eye-pair/Haar detection is used. Legacy skin/background and centered guesses are disabled.
- Person segmentation: MediaPipe ImageSegmenter `.task` when configured; otherwise geometric person mask from face/person estimates.
- Human parsing: configured SCHP/CIHP/LIP/ATR ONNX path is recorded, but a concrete adapter is still future work; coarse semantic masks are generated geometrically.
- Skin mask: semantic masks when available; color checks refine those masks but do not create standalone fallback skin regions.

Degraded outputs are marked with lower confidence and source values such as `geometric_fallback` or `fallback`.

## Skin Mask

V2 stores separate masks:

- `skin_semantic_mask`: semantic skin/face/neck/arm candidate intersected with person mask
- `skin_color_refine_mask`: YCrCb/Lab/HSV refinement sampled from semantic/person candidates
- `skin_final_mask`: edge-aware, protected-region-excluded final smoothing mask
- `skin_exclusion_mask`: eyes, eyebrows, lips, nostrils, teeth, hair, and clothes protection

`skin_final_mask` is passed into skin smoothing as an override so the old threshold-only refinement does not become the primary smoothing region when V2 is enabled.

## Body Regions

Regions required by downstream sliders are emitted as `RegionResult` values:

```text
face_region, jaw_region, left_eye_region, right_eye_region, nose_region,
mouth_region, neck_region, torso_region, waist_region, chest_region,
hip_region, left_arm_region, right_arm_region, left_leg_region,
right_leg_region, left_thigh_region, right_thigh_region, left_calf_region,
right_calf_region
```

Region sources are `semantic`, `landmark`, `geometric`, or `fallback`. Parser-backed masks are preferred. When parser weights are unavailable, coarse body regions are estimated from the person mask, face bbox, landmarks, and geometry with lower confidence.

## Debug Export

Use the CLI:

```bash
cd engine
.venv/bin/python -m beauty_engine.cli analyze ../demo/before.jpg /tmp/pixmeat-analysis --analysis-version v2
```

Or call `debug_render_masks` on a V2 session. Debug export writes:

```text
01_faces.png
02_face_landmarks.png
03_person_mask.png
04_human_parsing_labels.png
05_skin_semantic_mask.png
06_skin_color_refine_mask.png
07_skin_final_mask.png
08_body_regions.png
09_confidence_map.png
analysis_v2.json
```

These files are meant to diagnose face selection, background leakage, person coverage, parser quality, final smoothing coverage, and per-stage confidence.
