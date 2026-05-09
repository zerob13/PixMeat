from __future__ import annotations

import cv2
import numpy as np

from beauty_engine import landmark_indices as idx
from beauty_engine.masks import dilate, feather, polygon_mask, region_union
from beauty_engine.types import FaceResult, PersonResult, RegionResult, mask_bbox

REQUIRED_REGIONS = [
    "face_region",
    "jaw_region",
    "left_eye_region",
    "right_eye_region",
    "nose_region",
    "mouth_region",
    "neck_region",
    "torso_region",
    "waist_region",
    "chest_region",
    "hip_region",
    "left_arm_region",
    "right_arm_region",
    "left_leg_region",
    "right_leg_region",
    "left_thigh_region",
    "right_thigh_region",
    "left_calf_region",
    "right_calf_region",
]


def build_regions(
    shape: tuple[int, int],
    faces: list[FaceResult],
    persons: list[PersonResult],
    parsing_masks: dict[str, np.ndarray],
    person_mask: np.ndarray,
    *,
    parsing_source: str = "model",
) -> dict[str, RegionResult]:
    """Build named region masks for downstream sliders."""

    height, width = shape
    regions: dict[str, RegionResult] = {}
    face = faces[0] if faces else None
    if face and face.landmarks is not None:
        face_size = max(face.bbox[2], face.bbox[3])
        regions["face_region"] = _region("face_region", _face_mask(shape, face), 0.85, "landmark")
        regions["jaw_region"] = _region("jaw_region", _jaw_mask(shape, face), 0.78, "landmark")
        regions["left_eye_region"] = _region("left_eye_region", _landmark_region(shape, face, [idx.LEFT_EYE], face_size), 0.82, "landmark")
        regions["right_eye_region"] = _region("right_eye_region", _landmark_region(shape, face, [idx.RIGHT_EYE], face_size), 0.82, "landmark")
        regions["nose_region"] = _region("nose_region", _landmark_region(shape, face, [idx.NOSE_LEFT, idx.NOSE_RIGHT], face_size), 0.78, "landmark")
        regions["mouth_region"] = _region("mouth_region", _landmark_region(shape, face, [idx.OUTER_LIPS, idx.INNER_LIPS], face_size), 0.82, "landmark")
    elif face:
        regions["face_region"] = _region("face_region", _ellipse_from_bbox(shape, face.bbox, 0.50, 0.55), 0.40, "geometric")

    for name, parsing_name in [
        ("neck_region", "neck"),
        ("torso_region", "torso"),
        ("left_arm_region", "left_arm"),
        ("right_arm_region", "right_arm"),
        ("left_leg_region", "left_leg"),
        ("right_leg_region", "right_leg"),
    ]:
        mask = parsing_masks.get(parsing_name, np.zeros((height, width), dtype=np.float32))
        has_mask = float(mask.max(initial=0)) > 0
        source = _region_source_from_parsing(parsing_source, has_mask)
        confidence = _region_confidence_from_source(source)
        regions[name] = _region(name, mask, confidence, source)

    torso = regions.get("torso_region")
    torso_mask = torso.mask if torso else np.zeros((height, width), dtype=np.float32)
    torso_bbox = mask_bbox(torso_mask) if np.any(torso_mask > 0.05) else (0.0, 0.0, 0.0, 0.0)
    if torso_bbox[2] <= 0 and persons:
        torso_bbox = _upper_body_bbox(persons[0].bbox)
        torso_mask = _rect_mask(shape, torso_bbox)

    regions["chest_region"] = _region("chest_region", _vertical_slice(torso_mask, 0.05, 0.38), 0.52, "geometric")
    regions["waist_region"] = _region("waist_region", _vertical_slice(torso_mask, 0.38, 0.68), 0.52, "geometric")
    regions["hip_region"] = _region("hip_region", _vertical_slice(torso_mask, 0.68, 1.00), 0.48, "geometric")

    for side in ("left", "right"):
        leg = regions.get(f"{side}_leg_region")
        leg_mask = leg.mask if leg else np.zeros((height, width), dtype=np.float32)
        regions[f"{side}_thigh_region"] = _region(f"{side}_thigh_region", _vertical_slice(leg_mask, 0.00, 0.52), 0.42, "geometric")
        regions[f"{side}_calf_region"] = _region(f"{side}_calf_region", _vertical_slice(leg_mask, 0.48, 1.00), 0.42, "geometric")

    for name in REQUIRED_REGIONS:
        if name not in regions:
            regions[name] = _region(name, np.zeros((height, width), dtype=np.float32), 0.0, "fallback")

    return regions


def _region_source_from_parsing(parsing_source: str, has_mask: bool) -> str:
    if not has_mask:
        return "fallback"
    if parsing_source == "model":
        return "semantic"
    if parsing_source == "geometric_fallback":
        return "geometric"
    return "fallback"


def _region_confidence_from_source(source: str) -> float:
    if source == "semantic":
        return 0.65
    if source == "geometric":
        return 0.35
    return 0.20


def regions_union(regions: dict[str, RegionResult], names: list[str]) -> np.ndarray:
    masks = [regions[name].mask for name in names if name in regions]
    if not masks:
        return np.zeros((1, 1), dtype=np.float32)
    return np.clip(np.maximum.reduce(masks), 0, 1).astype(np.float32)


def _region(name: str, mask: np.ndarray, confidence: float, source: str) -> RegionResult:
    clean = np.clip(mask.astype(np.float32), 0, 1)
    return RegionResult(name=name, mask=clean, bbox=mask_bbox(clean), confidence=confidence, source=source)


def _face_mask(shape: tuple[int, int], face: FaceResult) -> np.ndarray:
    if face.landmarks is not None and face.landmarks.shape[0] > max(idx.FACE_OVAL):
        mask = polygon_mask(shape, face.landmarks[idx.FACE_OVAL, :2])
        return feather(mask, max(1.0, face.bbox[2] * 0.018))
    return _ellipse_from_bbox(shape, face.bbox, 0.50, 0.55)


def _jaw_mask(shape: tuple[int, int], face: FaceResult) -> np.ndarray:
    if face.landmarks is None or face.landmarks.shape[0] <= max(idx.LEFT_JAW + idx.RIGHT_JAW + idx.CHIN):
        return _ellipse_from_bbox(shape, face.bbox, 0.48, 0.25, y_offset=0.25)
    points = face.landmarks[idx.LEFT_JAW + idx.RIGHT_JAW + idx.CHIN, :2]
    mask = polygon_mask(shape, points)
    return feather(dilate(mask, max(1, int(face.bbox[2] * 0.030))), max(1.0, face.bbox[2] * 0.012))


def _landmark_region(shape: tuple[int, int], face: FaceResult, groups: list[list[int]], face_size: float) -> np.ndarray:
    if face.landmarks is None:
        return np.zeros(shape, dtype=np.float32)
    mask = region_union(shape, face.landmarks, groups)
    return feather(dilate(mask, max(1, int(face_size * 0.020))), max(1.0, face_size * 0.010))


def _ellipse_from_bbox(
    shape: tuple[int, int],
    bbox: tuple[float, float, float, float],
    rx: float,
    ry: float,
    *,
    y_offset: float = 0.0,
) -> np.ndarray:
    height, width = shape
    x, y, w, h = bbox
    mask = np.zeros((height, width), dtype=np.float32)
    cv2.ellipse(mask, (int(x + w * 0.5), int(y + h * (0.5 + y_offset))), (int(w * rx), int(h * ry)), 0, 0, 360, 1.0, -1)
    return feather(mask, max(1.0, w * 0.018))


def _upper_body_bbox(person_bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, w, h = person_bbox
    return (x, y + h * 0.18, w, h * 0.44)


def _rect_mask(shape: tuple[int, int], bbox: tuple[float, float, float, float]) -> np.ndarray:
    height, width = shape
    x, y, w, h = [int(round(value)) for value in bbox]
    mask = np.zeros((height, width), dtype=np.float32)
    cv2.rectangle(mask, (max(0, x), max(0, y)), (min(width - 1, x + w), min(height - 1, y + h)), 1.0, -1)
    return feather(mask, max(1.0, min(width, height) * 0.006))


def _vertical_slice(mask: np.ndarray, top_ratio: float, bottom_ratio: float) -> np.ndarray:
    bbox = mask_bbox(mask)
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return np.zeros_like(mask, dtype=np.float32)
    top = int(y + h * top_ratio)
    bottom = int(y + h * bottom_ratio)
    sliced = np.zeros_like(mask, dtype=np.float32)
    sliced[top:bottom, :] = mask[top:bottom, :]
    return feather(sliced, max(1.0, h * 0.012))
