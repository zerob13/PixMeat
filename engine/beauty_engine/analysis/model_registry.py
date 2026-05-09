from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any

from beauty_engine.models.model_config import AnalysisConfig
from beauty_engine.types import ModelBackendInfo


@dataclass
class LoadedModel:
    """Cached model instance plus diagnostics."""

    model: Any | None
    info: ModelBackendInfo


class ModelRegistry:
    """Loads and caches optional Analysis V2 models from configured local paths."""

    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config
        self._cache: dict[str, LoadedModel] = {}
        self.backend_info: dict[str, ModelBackendInfo] = {}

    def get_face_landmarker(self) -> LoadedModel:
        return self._get_or_load("face_landmarker", self._load_mediapipe_face_landmarker)

    def get_face_detector(self) -> LoadedModel:
        return self._get_or_load("face_detector", self._load_onnx_model)

    def get_person_segmenter(self) -> LoadedModel:
        return self._get_or_load("person_segmentation", self._load_segmentation_model)

    def get_human_parser(self) -> LoadedModel:
        return self._get_or_load("human_parsing", self._load_onnx_model)

    def close(self) -> None:
        for loaded in self._cache.values():
            close = getattr(loaded.model, "close", None)
            if callable(close):
                close()
        self._cache.clear()

    def _get_or_load(self, key: str, loader) -> LoadedModel:
        if key not in self._cache:
            started = time.perf_counter()
            loaded = loader(key)
            elapsed = int((time.perf_counter() - started) * 1000)
            info = ModelBackendInfo(
                name=loaded.info.name,
                backend=loaded.info.backend,
                provider=loaded.info.provider,
                model_path=loaded.info.model_path,
                available=loaded.info.available,
                source=loaded.info.source,
                message=loaded.info.message,
                elapsed_ms=elapsed,
            )
            loaded = LoadedModel(loaded.model, info)
            self._cache[key] = loaded
            self.backend_info[key] = info
        return self._cache[key]

    def _load_mediapipe_face_landmarker(self, key: str) -> LoadedModel:
        path = self.config.resolve_model_path(key)
        if not path:
            return self._missing(key, "MediaPipe Face Landmarker model path is not configured")
        try:
            face_landmarker = importlib.import_module("mediapipe.tasks.python.vision.face_landmarker")
            base_options = importlib.import_module("mediapipe.tasks.python.core.base_options")
            running_mode = importlib.import_module("mediapipe.tasks.python.vision.core.vision_task_running_mode")
            options = face_landmarker.FaceLandmarkerOptions(
                base_options=base_options.BaseOptions(model_asset_path=path),
                running_mode=running_mode.VisionTaskRunningMode.IMAGE,
                num_faces=8,
                min_face_detection_confidence=0.30,
                min_face_presence_confidence=0.30,
            )
            model = face_landmarker.FaceLandmarker.create_from_options(options)
            return LoadedModel(model, self._available(key, path, "mediapipe_tasks", "cpu"))
        except Exception as exc:
            return self._unavailable(key, path, f"Cannot load MediaPipe Face Landmarker: {exc}")

    def _load_segmentation_model(self, key: str) -> LoadedModel:
        path = self.config.resolve_model_path(key)
        if not path:
            return self._missing(key, "Person segmentation model path is not configured")
        if path.endswith(".task"):
            return self._load_mediapipe_image_segmenter(key, path)
        return self._load_onnx_model(key)

    def _load_mediapipe_image_segmenter(self, key: str, path: str) -> LoadedModel:
        try:
            image_segmenter = importlib.import_module("mediapipe.tasks.python.vision.image_segmenter")
            base_options = importlib.import_module("mediapipe.tasks.python.core.base_options")
            running_mode = importlib.import_module("mediapipe.tasks.python.vision.core.vision_task_running_mode")
            options = image_segmenter.ImageSegmenterOptions(
                base_options=base_options.BaseOptions(model_asset_path=path),
                running_mode=running_mode.VisionTaskRunningMode.IMAGE,
                output_category_mask=True,
            )
            model = image_segmenter.ImageSegmenter.create_from_options(options)
            return LoadedModel(model, self._available(key, path, "mediapipe_tasks", "cpu"))
        except Exception as exc:
            return self._unavailable(key, path, f"Cannot load MediaPipe segmenter: {exc}")

    def _load_onnx_model(self, key: str) -> LoadedModel:
        path = self.config.resolve_model_path(key)
        if not path:
            return self._missing(key, "Model path is not configured")
        try:
            ort = importlib.import_module("onnxruntime")
            providers = self._onnx_providers(ort)
            session = ort.InferenceSession(path, providers=providers)
            provider = session.get_providers()[0] if session.get_providers() else "CPUExecutionProvider"
            backend = "cuda" if "CUDA" in provider else "cpu"
            return LoadedModel(session, self._available(key, path, provider, backend))
        except Exception as exc:
            return self._unavailable(key, path, f"Cannot load ONNX model: {exc}")

    def _onnx_providers(self, ort) -> list[str]:
        available = set(ort.get_available_providers())
        if self.config.device in {"auto", "cuda"} and "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def _available(self, key: str, path: str, provider: str, backend: str) -> ModelBackendInfo:
        return ModelBackendInfo(key, backend, provider, path, True, "model", "")

    def _missing(self, key: str, message: str) -> LoadedModel:
        info = ModelBackendInfo(key, "cpu", "fallback", None, False, "fallback", message)
        return LoadedModel(None, info)

    def _unavailable(self, key: str, path: str, message: str) -> LoadedModel:
        info = ModelBackendInfo(key, "cpu", "fallback", path, False, "fallback", message)
        return LoadedModel(None, info)
