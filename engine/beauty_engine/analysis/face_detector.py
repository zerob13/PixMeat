from __future__ import annotations

import time

import cv2
import numpy as np

from beauty_engine.face import detect_faces
from beauty_engine.types import FaceResult, clamp_bbox, expand_bbox

from .confidence import estimate_face_quality, score_face_bbox
from .model_registry import ModelRegistry


class FaceDetectorV2:
    """Face detector wrapper with model diagnostics and safe classic detection."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def detect(self, image_bgr: np.ndarray) -> list[FaceResult]:
        model_faces = self._detect_model_placeholder(image_bgr)
        if model_faces:
            return model_faces
        return self._detect_current_fallback(image_bgr)

    def _detect_model_placeholder(self, image_bgr: np.ndarray) -> list[FaceResult]:
        loaded = self.registry.get_face_detector()
        if loaded.model is None:
            return []
        # SCRFD/RetinaFace ONNX variants have different input sizes and decode heads.
        # Keep the model load diagnostic here and use MediaPipe Face Landmarker or
        # the current detector until a concrete adapter is configured.
        self.registry.backend_info["face_detector"] = loaded.info.__class__(
            loaded.info.name,
            loaded.info.backend,
            loaded.info.provider,
            loaded.info.model_path,
            False,
            "fallback",
            "Configured face detector loaded, but no SCRFD/RetinaFace adapter is selected",
            loaded.info.elapsed_ms,
        )
        return []

    def _detect_current_fallback(self, image_bgr: np.ndarray) -> list[FaceResult]:
        started = time.perf_counter()
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        fallback_faces = detect_faces(rgb, allow_skin=False, allow_heuristic=False)
        height, width = image_bgr.shape[:2]
        faces: list[FaceResult] = []
        for index, face in enumerate(fallback_faces, start=1):
            bbox = clamp_bbox(face.bbox, width, height)
            points = face.points_px(width, height)
            refined_bbox = _tighten_bbox_from_points_and_skin(rgb, bbox, points)
            expanded = expand_bbox(refined_bbox, 1.35, width, height)
            confidence = float(np.clip(face.confidence, 0.35, 0.78))
            score = score_face_bbox(refined_bbox, (width, height), confidence)
            quality = estimate_face_quality(points, refined_bbox, (width, height), confidence)
            faces.append(
                FaceResult(
                    face_id=f"face_{index}",
                    bbox=refined_bbox,
                    expanded_bbox=expanded,
                    score=score,
                    confidence=confidence,
                    source="classic_face_detector",
                    landmarks=points,
                    quality=quality,
                )
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        info = self.registry.backend_info.get("face_detector")
        if info:
            self.registry.backend_info["face_detector"] = info.__class__(
                info.name, info.backend, info.provider, info.model_path, info.available, info.source, info.message, elapsed
            )
        return sorted(faces, key=lambda face: face.score, reverse=True)


def _tighten_bbox_from_points_and_skin(rgb: np.ndarray, bbox: tuple[float, float, float, float], points: np.ndarray) -> tuple[float, float, float, float]:
    height, width = rgb.shape[:2]
    if points.size:
        finite = np.isfinite(points[:, :2]).all(axis=1)
        valid = points[finite, :2]
        if valid.size:
            x1, y1 = np.percentile(valid, 3, axis=0)
            x2, y2 = np.percentile(valid, 97, axis=0)
            point_bbox = clamp_bbox((float(x1), float(y1), float(x2 - x1), float(y2 - y1)), width, height)
            if point_bbox[2] > 12 and point_bbox[3] > 12:
                return expand_bbox(point_bbox, 1.08, width, height)
    return clamp_bbox(bbox, width, height)
