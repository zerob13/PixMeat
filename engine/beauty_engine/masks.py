from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from . import landmark_indices as idx
from .face import FaceLandmarks


@dataclass(frozen=True)
class RegionMasks:
    face: np.ndarray
    skin: np.ndarray
    eyes: np.ndarray
    mouth: np.ndarray
    teeth: np.ndarray
    protected: np.ndarray


def build_masks(shape: tuple[int, int], face: FaceLandmarks) -> RegionMasks:
    height, width = shape
    points = face.points_px(width, height)
    face_size = max(face.bbox[2], face.bbox[3])
    face_mask = polygon_mask((height, width), points[idx.FACE_OVAL, :2])
    face_mask = dilate(face_mask, max(2, int(face_size * 0.025)))
    face_mask = feather(face_mask, max(1.5, face_size * 0.018))

    eye_mask = region_union((height, width), points, [idx.LEFT_EYE, idx.RIGHT_EYE])
    eye_mask = dilate(eye_mask, max(2, int(face_size * 0.025)))
    eye_mask = feather(eye_mask, max(1.2, face_size * 0.012))

    brow_mask = region_union((height, width), points, [idx.LEFT_EYEBROW, idx.RIGHT_EYEBROW])
    brow_mask = dilate(brow_mask, max(2, int(face_size * 0.02)))
    brow_mask = feather(brow_mask, max(1.0, face_size * 0.01))

    mouth_mask = region_union((height, width), points, [idx.OUTER_LIPS, idx.INNER_LIPS])
    mouth_mask = dilate(mouth_mask, max(2, int(face_size * 0.02)))
    mouth_mask = feather(mouth_mask, max(1.0, face_size * 0.012))

    nose_mask = region_union((height, width), points, [idx.NOSE_LEFT, idx.NOSE_RIGHT])
    nose_mask = dilate(nose_mask, max(1, int(face_size * 0.015)))
    nose_mask = feather(nose_mask, max(0.8, face_size * 0.008))

    hairline = upper_face_reduction((height, width), face)
    protected = np.clip(eye_mask + brow_mask + mouth_mask + nose_mask + hairline, 0, 1)
    skin = np.clip(face_mask - protected * 0.9, 0, 1)
    skin = feather(skin, max(1.0, face_size * 0.008))

    teeth = polygon_mask((height, width), points[idx.INNER_LIPS, :2])
    teeth = feather(teeth, max(0.8, face_size * 0.006))

    return RegionMasks(face=face_mask, skin=skin, eyes=eye_mask, mouth=mouth_mask, teeth=teeth, protected=protected)


def polygon_mask(shape: tuple[int, int], polygon: np.ndarray) -> np.ndarray:
    height, width = shape
    mask = np.zeros((height, width), dtype=np.float32)
    if polygon.size == 0:
        return mask
    pts = np.round(polygon).astype(np.int32)
    pts[:, 0] = np.clip(pts[:, 0], 0, width - 1)
    pts[:, 1] = np.clip(pts[:, 1], 0, height - 1)
    cv2.fillPoly(mask, [pts], 1.0)
    return mask


def region_union(shape: tuple[int, int], points: np.ndarray, regions: list[list[int]]) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.float32)
    for region in regions:
        mask = np.maximum(mask, polygon_mask(shape, points[region, :2]))
    return mask


def feather(mask: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return np.clip(mask, 0, 1).astype(np.float32)
    kernel = max(3, int(round(sigma * 6)) | 1)
    blurred = cv2.GaussianBlur(mask.astype(np.float32), (kernel, kernel), sigmaX=sigma, sigmaY=sigma)
    return np.clip(blurred, 0, 1).astype(np.float32)


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.astype(np.float32)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
    return cv2.dilate(mask.astype(np.float32), kernel)


def upper_face_reduction(shape: tuple[int, int], face: FaceLandmarks) -> np.ndarray:
    height, width = shape
    x, y, w, h = face.bbox
    mask = np.zeros((height, width), dtype=np.float32)
    top = int(max(0, y))
    bottom = int(min(height, y + h * 0.25))
    left = int(max(0, x))
    right = int(min(width, x + w))
    if bottom <= top or right <= left:
        return mask
    gradient = np.linspace(1.0, 0.0, bottom - top, dtype=np.float32)[:, None]
    mask[top:bottom, left:right] = gradient
    return feather(mask, max(1, h * 0.015))
