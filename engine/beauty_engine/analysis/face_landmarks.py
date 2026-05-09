from __future__ import annotations

import importlib
import time

import cv2
import numpy as np

from beauty_engine import landmark_indices as idx
from beauty_engine.face import _synthetic_landmarks
from beauty_engine.types import BBox, FaceResult, clamp_bbox, expand_bbox

from .confidence import estimate_face_quality, score_face_bbox
from .model_registry import ModelRegistry


class FaceLandmarkRunner:
    """Runs model-backed face landmarks and maps them to original coordinates."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def detect_full_image(self, image_bgr: np.ndarray) -> list[FaceResult]:
        loaded = self.registry.get_face_landmarker()
        if loaded.model is None:
            return []
        started = time.perf_counter()
        try:
            result = loaded.model.detect(_mp_image_from_bgr(image_bgr))
        except Exception as exc:
            self.registry.backend_info["face_landmarker"] = loaded.info.__class__(
                loaded.info.name,
                loaded.info.backend,
                loaded.info.provider,
                loaded.info.model_path,
                False,
                "fallback",
                f"Face Landmarker inference failed: {exc}",
                loaded.info.elapsed_ms,
            )
            return []
        finally:
            elapsed = int((time.perf_counter() - started) * 1000)
            info = self.registry.backend_info.get("face_landmarker")
            if info:
                self.registry.backend_info["face_landmarker"] = info.__class__(
                    info.name, info.backend, info.provider, info.model_path, info.available, info.source, info.message, elapsed
                )

        height, width = image_bgr.shape[:2]
        faces: list[FaceResult] = []
        for index, landmarks in enumerate(result.face_landmarks or [], start=1):
            points = np.asarray([[lm.x * width, lm.y * height, lm.z] for lm in landmarks], dtype=np.float32)
            if points.shape[0] == 0:
                continue
            bbox = _bbox_from_landmarks(points, width, height)
            expanded = expand_bbox(bbox, 1.35, width, height)
            score = score_face_bbox(bbox, (width, height), 0.96)
            quality = estimate_face_quality(points, bbox, (width, height), 0.96)
            faces.append(
                FaceResult(
                    face_id=f"face_{index}",
                    bbox=bbox,
                    expanded_bbox=expanded,
                    score=score,
                    confidence=0.96,
                    source="mediapipe_face_landmarker",
                    landmarks=points,
                    quality=quality,
                )
            )
        return sorted(faces, key=lambda face: face.score, reverse=True)

    def landmark_faces(self, image_bgr: np.ndarray, faces: list[FaceResult]) -> list[FaceResult]:
        """Fill missing landmarks using crop inference or synthetic fallback."""

        loaded = self.registry.get_face_landmarker()
        height, width = image_bgr.shape[:2]
        output: list[FaceResult] = []
        for face in faces:
            if face.landmarks is not None:
                output.append(face)
                continue
            points = None
            source = face.source
            confidence = face.confidence
            if loaded.model is not None:
                crop_bbox = expand_bbox(face.bbox, 1.35, width, height)
                crop = crop_bgr(image_bgr, crop_bbox)
                if crop.size:
                    try:
                        result = loaded.model.detect(_mp_image_from_bgr(crop))
                        if result.face_landmarks:
                            crop_points = np.asarray(
                                [[lm.x, lm.y, lm.z] for lm in result.face_landmarks[0]],
                                dtype=np.float32,
                            )
                            points = map_crop_landmarks_to_original(crop_points, crop_bbox, (width, height), normalized=True)
                            source = f"{source}+mediapipe_crop_landmarks"
                            confidence = max(confidence, 0.88)
                    except Exception:
                        points = None
            if points is None:
                synthetic = _synthetic_landmarks(face.bbox, width, height)
                points = synthetic.copy()
                points[:, 0] *= width
                points[:, 1] *= height
                source = f"{source}+synthetic_landmarks"
                confidence = min(confidence, 0.62)
            quality = estimate_face_quality(points, face.bbox, (width, height), confidence)
            output.append(
                FaceResult(
                    face_id=face.face_id,
                    bbox=face.bbox,
                    expanded_bbox=face.expanded_bbox,
                    score=face.score,
                    confidence=confidence,
                    source=source,
                    landmarks=points,
                    quality=quality,
                )
            )
        return output


def crop_bgr(image_bgr: np.ndarray, bbox: BBox) -> np.ndarray:
    x, y, w, h = [int(round(value)) for value in bbox]
    height, width = image_bgr.shape[:2]
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    x2 = max(x + 1, min(width, x + max(1, w)))
    y2 = max(y + 1, min(height, y + max(1, h)))
    return image_bgr[y:y2, x:x2]


def map_crop_landmarks_to_original(
    landmarks: np.ndarray,
    crop_bbox: BBox,
    image_size: tuple[int, int],
    *,
    normalized: bool,
) -> np.ndarray:
    """Map crop-local landmarks back to original image coordinates."""

    width, height = image_size
    x, y, w, h = crop_bbox
    points = np.asarray(landmarks, dtype=np.float32).copy()
    if points.ndim != 2 or points.shape[1] < 2:
        raise ValueError("landmarks must be shaped Nx2 or Nx3")
    if normalized:
        points[:, 0] = x + points[:, 0] * w
        points[:, 1] = y + points[:, 1] * h
    else:
        points[:, 0] = x + points[:, 0]
        points[:, 1] = y + points[:, 1]
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    return points


def _bbox_from_landmarks(points: np.ndarray, width: int, height: int) -> BBox:
    indices = idx.FACE_OVAL if points.shape[0] > max(idx.FACE_OVAL) else list(range(points.shape[0]))
    face_points = points[indices, :2]
    x_min, y_min = np.min(face_points, axis=0)
    x_max, y_max = np.max(face_points, axis=0)
    return clamp_bbox((float(x_min), float(y_min), float(x_max - x_min), float(y_max - y_min)), width, height)


def _mp_image_from_bgr(image_bgr: np.ndarray):
    mp_image = importlib.import_module("mediapipe.tasks.python.vision.core.image")
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    rgb = np.ascontiguousarray(rgb.astype(np.uint8))
    return mp_image.Image(mp_image.ImageFormat.SRGB, rgb)
