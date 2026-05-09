# Local Model Assets

Place optional Analysis V2 model weights here for packaged or offline development builds.

Recognized names include:

- `face_landmarker.task`
- `face_detector.onnx`
- `scrfd.onnx`
- `retinaface.onnx`
- `selfie_segmenter.task`
- `person_segmentation.onnx`
- `modnet.onnx`
- `birefnet.onnx`
- `human_parsing.onnx`
- `schp.onnx`
- `cihp.onnx`
- `lip.onnx`
- `atr.onnx`

The engine never downloads weights at runtime. Large model files should be supplied through release assets or local configuration rather than committed blindly.
