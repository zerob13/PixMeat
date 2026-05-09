from __future__ import annotations

import time

import cv2
import numpy as np

from beauty_engine.types import FaceResult, PersonResult, mask_bbox

from .face_landmarks import _mp_image_from_bgr
from .model_registry import ModelRegistry


class PersonSegmenterV2:
    """Person segmentation wrapper with model path support and geometric fallback."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def segment(self, image_bgr: np.ndarray, faces: list[FaceResult]) -> tuple[np.ndarray, list[PersonResult], float, str]:
        loaded = self.registry.get_person_segmenter()
        if loaded.model is not None and loaded.info.provider == "mediapipe_tasks":
            mask = self._segment_mediapipe(image_bgr, loaded.model)
            if mask is not None:
                cleaned = cleanup_person_mask(mask)
                return self._result_from_mask(cleaned, 0.82, "model")
        elif loaded.model is not None:
            self.registry.backend_info["person_segmentation"] = loaded.info.__class__(
                loaded.info.name,
                loaded.info.backend,
                loaded.info.provider,
                loaded.info.model_path,
                False,
                "fallback",
                "Generic ONNX person segmentation adapter is not configured",
                loaded.info.elapsed_ms,
            )

        mask = geometric_person_mask(image_bgr.shape[:2], faces)
        cleaned = cleanup_person_mask(mask)
        return self._result_from_mask(cleaned, 0.38 if faces else 0.22, "geometric_fallback")

    def _segment_mediapipe(self, image_bgr: np.ndarray, model) -> np.ndarray | None:
        started = time.perf_counter()
        try:
            result = model.segment(_mp_image_from_bgr(image_bgr))
        except Exception:
            return None
        finally:
            info = self.registry.backend_info.get("person_segmentation")
            if info:
                self.registry.backend_info["person_segmentation"] = info.__class__(
                    info.name,
                    info.backend,
                    info.provider,
                    info.model_path,
                    info.available,
                    info.source,
                    info.message,
                    int((time.perf_counter() - started) * 1000),
                )
        category_mask = getattr(result, "category_mask", None)
        if category_mask is None:
            return None
        arr = np.asarray(category_mask.numpy_view(), dtype=np.float32)
        if arr.ndim != 2:
            return None
        if arr.max() > 1.0:
            arr = (arr > 0).astype(np.float32)
        return np.clip(arr, 0, 1)

    def _result_from_mask(self, mask: np.ndarray, confidence: float, source: str) -> tuple[np.ndarray, list[PersonResult], float, str]:
        bbox = mask_bbox(mask, threshold=0.08)
        persons = [] if bbox[2] <= 0 or bbox[3] <= 0 else [PersonResult("person_1", bbox, confidence, source)]
        return mask, persons, confidence, source


def cleanup_person_mask(mask: np.ndarray, *, min_area_ratio: float = 0.002) -> np.ndarray:
    """Clean, feather, and remove tiny person-mask components."""

    arr = np.clip(mask.astype(np.float32), 0, 1)
    height, width = arr.shape[:2]
    binary = (arr > 0.18).astype(np.uint8)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_large)
    binary = remove_tiny_components(binary, min_area=max(16, int(height * width * min_area_ratio)))
    distance_in = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    distance_out = cv2.distanceTransform(1 - binary, cv2.DIST_L2, 5)
    feather = np.clip((distance_in - distance_out + 8.0) / 16.0, 0, 1)
    soft = cv2.GaussianBlur(feather.astype(np.float32), (0, 0), sigmaX=2.0)
    return np.clip(soft, 0, 1).astype(np.float32)


def remove_tiny_components(binary: np.ndarray, min_area: int) -> np.ndarray:
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats((binary > 0).astype(np.uint8), 8)
    output = np.zeros_like(binary, dtype=np.uint8)
    if count <= 1:
        return output
    largest = max(int(stats[label, cv2.CC_STAT_AREA]) for label in range(1, count))
    threshold = min(min_area, largest)
    for label in range(1, count):
        if int(stats[label, cv2.CC_STAT_AREA]) >= threshold:
            output[labels == label] = 1
    return output


def geometric_person_mask(shape: tuple[int, int], faces: list[FaceResult]) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.float32)
    if faces:
        face = faces[0]
        x, y, face_w, face_h = face.bbox
        cx = x + face_w * 0.5
        top = max(0.0, y - face_h * 0.10)
        bottom = min(float(height - 1), y + face_h * 5.2)
        body_h = max(face_h * 1.2, bottom - top)
        torso_center_y = y + face_h * 2.35
        cv2.ellipse(
            mask,
            (int(round(cx)), int(round(torso_center_y))),
            (int(round(face_w * 1.55)), int(round(body_h * 0.42))),
            0,
            0,
            360,
            1.0,
            -1,
        )
        cv2.ellipse(
            mask,
            (int(round(cx)), int(round(y + face_h * 0.52))),
            (int(round(face_w * 0.72)), int(round(face_h * 0.75))),
            0,
            0,
            360,
            1.0,
            -1,
        )
        arm_y1 = y + face_h * 1.55
        arm_y2 = min(height - 1, y + face_h * 4.80)
        cv2.line(mask, (int(cx - face_w * 1.25), int(arm_y1)), (int(cx - face_w * 3.15), int(arm_y2)), 1.0, max(8, int(face_w * 0.36)))
        cv2.line(mask, (int(cx + face_w * 1.25), int(arm_y1)), (int(cx + face_w * 3.15), int(arm_y2)), 1.0, max(8, int(face_w * 0.36)))
    else:
        cv2.ellipse(mask, (width // 2, int(height * 0.58)), (int(width * 0.28), int(height * 0.38)), 0, 0, 360, 1.0, -1)
    return np.clip(mask, 0, 1).astype(np.float32)
