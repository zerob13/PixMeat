from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

BBox = tuple[float, float, float, float]
ImageSize = tuple[int, int]


@dataclass(frozen=True)
class ModelBackendInfo:
    """Runtime status for one analysis model slot."""

    name: str
    backend: str
    provider: str
    model_path: str | None
    available: bool
    source: str
    message: str = ""
    elapsed_ms: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "backend": self.backend,
            "provider": self.provider,
            "model_path": self.model_path,
            "available": self.available,
            "source": self.source,
            "message": self.message,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class FaceQuality:
    """Quality hints used to gate riskier face sliders."""

    face_size_ratio: float
    landmark_confidence: float
    yaw_hint: float
    pitch_hint: float
    roll_hint: float
    is_profile_hint: bool
    unavailable_sliders: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "face_size_ratio": self.face_size_ratio,
            "landmark_confidence": self.landmark_confidence,
            "yaw_hint": self.yaw_hint,
            "pitch_hint": self.pitch_hint,
            "roll_hint": self.roll_hint,
            "is_profile_hint": self.is_profile_hint,
            "unavailable_sliders": self.unavailable_sliders,
        }


@dataclass(frozen=True)
class FaceResult:
    """Detected face with optional landmarks in original image coordinates."""

    face_id: str
    bbox: BBox
    expanded_bbox: BBox
    score: float
    confidence: float
    source: str
    landmarks: np.ndarray | None = None
    quality: FaceQuality | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "face_id": self.face_id,
            "bbox": bbox_to_json(self.bbox),
            "expanded_bbox": bbox_to_json(self.expanded_bbox),
            "score": float(self.score),
            "confidence": float(self.confidence),
            "source": self.source,
            "landmark_count": int(self.landmarks.shape[0]) if self.landmarks is not None else 0,
            "quality": self.quality.to_json() if self.quality else None,
        }


@dataclass(frozen=True)
class PersonResult:
    """Visible person candidate and confidence metadata."""

    person_id: str
    bbox: BBox
    confidence: float
    source: str

    def to_json(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "bbox": bbox_to_json(self.bbox),
            "confidence": float(self.confidence),
            "source": self.source,
        }


@dataclass(frozen=True)
class RegionResult:
    """Named semantic or geometric region mask."""

    name: str
    mask: np.ndarray
    bbox: BBox
    confidence: float
    source: str

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bbox": bbox_to_json(self.bbox),
            "confidence": float(self.confidence),
            "source": self.source,
            "mask": mask_summary(self.mask),
        }


@dataclass(frozen=True)
class AnalysisConfidence:
    """Aggregate analysis confidence grouped by stage."""

    face_detection: float
    face_landmarks: float
    person_segmentation: float
    human_parsing: float
    skin_mask: float
    overall: float

    def to_json(self) -> dict[str, float]:
        return {
            "face_detection": float(self.face_detection),
            "face_landmarks": float(self.face_landmarks),
            "person_segmentation": float(self.person_segmentation),
            "human_parsing": float(self.human_parsing),
            "skin_mask": float(self.skin_mask),
            "overall": float(self.overall),
        }


@dataclass(frozen=True)
class AnalysisResult:
    """Complete Analysis V2 output.

    Masks and regions keep NumPy arrays in memory for retouching. The custom
    JSON serializer stores compact metadata so the schema remains serializable.
    """

    image_size: ImageSize
    faces: list[FaceResult]
    selected_face_id: str | None
    persons: list[PersonResult]
    selected_person_id: str | None
    masks: dict[str, np.ndarray]
    regions: dict[str, RegionResult]
    confidence: AnalysisConfidence
    debug: dict[str, Any]
    model_backends: dict[str, ModelBackendInfo]

    def to_json(self) -> dict[str, Any]:
        return {
            "image_size": [int(self.image_size[0]), int(self.image_size[1])],
            "faces": [face.to_json() for face in self.faces],
            "selected_face_id": self.selected_face_id,
            "persons": [person.to_json() for person in self.persons],
            "selected_person_id": self.selected_person_id,
            "masks": {name: mask_summary(mask) for name, mask in self.masks.items()},
            "regions": {name: region.to_json() for name, region in self.regions.items()},
            "confidence": self.confidence.to_json(),
            "debug": self.debug,
            "model_backends": {name: info.to_json() for name, info in self.model_backends.items()},
        }


def bbox_to_json(bbox: BBox) -> list[float]:
    return [float(value) for value in bbox]


def clamp_bbox(bbox: BBox, width: int, height: int) -> BBox:
    x, y, w, h = bbox
    x1 = float(np.clip(x, 0, max(0, width - 1)))
    y1 = float(np.clip(y, 0, max(0, height - 1)))
    x2 = float(np.clip(x + max(1.0, w), x1 + 1.0, width))
    y2 = float(np.clip(y + max(1.0, h), y1 + 1.0, height))
    return (x1, y1, x2 - x1, y2 - y1)


def expand_bbox(bbox: BBox, scale: float, width: int, height: int) -> BBox:
    x, y, w, h = bbox
    cx = x + w * 0.5
    cy = y + h * 0.5
    new_w = w * scale
    new_h = h * scale
    return clamp_bbox((cx - new_w * 0.5, cy - new_h * 0.5, new_w, new_h), width, height)


def mask_bbox(mask: np.ndarray, threshold: float = 0.05) -> BBox:
    ys, xs = np.where(mask > threshold)
    if xs.size == 0 or ys.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    x1 = float(xs.min())
    y1 = float(ys.min())
    x2 = float(xs.max() + 1)
    y2 = float(ys.max() + 1)
    return (x1, y1, x2 - x1, y2 - y1)


def mask_summary(mask: np.ndarray) -> dict[str, Any]:
    arr = np.asarray(mask, dtype=np.float32)
    return {
        "shape": [int(arr.shape[0]), int(arr.shape[1])] if arr.ndim >= 2 else list(arr.shape),
        "bbox": bbox_to_json(mask_bbox(arr)) if arr.ndim >= 2 else [0.0, 0.0, 0.0, 0.0],
        "mean": float(np.mean(arr)) if arr.size else 0.0,
        "max": float(np.max(arr)) if arr.size else 0.0,
        "coverage": float(np.mean(arr > 0.05)) if arr.size else 0.0,
    }
