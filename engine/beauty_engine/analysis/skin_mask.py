from __future__ import annotations

import cv2
import numpy as np

from beauty_engine import landmark_indices as idx
from beauty_engine.masks import dilate, feather, polygon_mask, region_union
from beauty_engine.smoothing import guided_filter, strong_edge_mask
from beauty_engine.types import FaceResult


def build_skin_masks_v2(
    image_bgr: np.ndarray,
    person_mask: np.ndarray,
    parsing_masks: dict[str, np.ndarray],
    faces: list[FaceResult],
) -> tuple[dict[str, np.ndarray], float]:
    """Build semantic, color-refined, and final skin masks."""

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    semantic = semantic_skin_mask(parsing_masks)
    semantic = np.minimum(semantic, person_mask)
    has_semantic_skin = bool(np.any(semantic > 0.1))
    color = skin_color_refine_mask(image_bgr, semantic) if has_semantic_skin else np.zeros_like(person_mask, dtype=np.float32)
    color = np.minimum(color, person_mask)
    base = np.maximum(semantic, color * 0.90)
    exclusion = exclusion_mask(image_bgr.shape[:2], faces, parsing_masks)
    base = np.clip(base - exclusion * 0.98, 0, 1)
    edges = strong_edge_mask(image_rgb, np.clip(base, 0, 1))
    base = np.clip(base * (1.0 - edges * 0.55), 0, 1)
    luma = _luma_rgb(image_rgb)
    final = guided_filter(luma, base.astype(np.float32), radius=16, eps=1e-3)
    final = cv2.GaussianBlur(np.clip(final, 0, 1), (0, 0), sigmaX=1.6)
    final = np.clip(final * person_mask, 0, 1).astype(np.float32)
    confidence = 0.70 if has_semantic_skin else 0.18
    return {
        "skin_semantic_mask": semantic.astype(np.float32),
        "skin_color_refine_mask": color.astype(np.float32),
        "skin_final_mask": final,
        "skin_exclusion_mask": exclusion.astype(np.float32),
    }, confidence


def semantic_skin_mask(parsing_masks: dict[str, np.ndarray]) -> np.ndarray:
    masks = [
        parsing_masks.get("skin"),
        parsing_masks.get("face"),
        parsing_masks.get("neck"),
        parsing_masks.get("left_arm"),
        parsing_masks.get("right_arm"),
    ]
    available = [mask for mask in masks if mask is not None]
    if not available:
        return np.zeros((1, 1), dtype=np.float32)
    return np.clip(np.maximum.reduce(available), 0, 1).astype(np.float32)


def skin_color_refine_mask(image_bgr: np.ndarray, sample_mask: np.ndarray) -> np.ndarray:
    image_u8 = image_bgr.astype(np.uint8)
    hsv = cv2.cvtColor(image_u8, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(image_u8, cv2.COLOR_BGR2YCrCb)
    lab = cv2.cvtColor(image_u8, cv2.COLOR_BGR2LAB).astype(np.float32)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    generic = (cr > 126) & (cr < 182) & (cb > 70) & (cb < 148) & (sat > 18) & (sat < 178) & (val > 36)
    warm = ((hue < 20) | (hue > 168)) & (sat > 18) & (sat < 172) & (val > 42) & (cr > 118) & (cb < 154)
    mask = generic | warm

    samples = lab[sample_mask > 0.35]
    if samples.shape[0] >= 48:
        center = np.median(samples[:, 1:3], axis=0)
        spread = np.percentile(np.abs(samples[:, 1:3] - center), 75, axis=0) + 5.0
        distance = np.sqrt(np.sum(((lab[:, :, 1:3] - center) / spread) ** 2, axis=2))
        mask = mask & (distance < 2.25)

    mask_f = mask.astype(np.float32)
    mask_f = cv2.morphologyEx(mask_f, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask_f = cv2.morphologyEx(mask_f, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return cv2.GaussianBlur(mask_f, (0, 0), sigmaX=1.8).astype(np.float32)


def exclusion_mask(shape: tuple[int, int], faces: list[FaceResult], parsing_masks: dict[str, np.ndarray]) -> np.ndarray:
    height, width = shape
    excluded = np.zeros((height, width), dtype=np.float32)
    for face in faces[:1]:
        if face.landmarks is None or face.landmarks.shape[0] <= max(idx.ALL_PROTECTED + idx.NOSE_TIP):
            continue
        points = face.landmarks
        face_size = max(face.bbox[2], face.bbox[3])
        eyes = region_union((height, width), points, [idx.LEFT_EYE, idx.RIGHT_EYE])
        brows = region_union((height, width), points, [idx.LEFT_EYEBROW, idx.RIGHT_EYEBROW])
        lips = region_union((height, width), points, [idx.OUTER_LIPS, idx.INNER_LIPS])
        nose = region_union((height, width), points, [idx.NOSE_LEFT, idx.NOSE_RIGHT])
        teeth = polygon_mask((height, width), points[idx.INNER_LIPS, :2])
        protected = eyes + brows + lips + nose * 0.8 + teeth
        protected = dilate(protected, max(1, int(face_size * 0.018)))
        excluded = np.maximum(excluded, feather(protected, max(1.0, face_size * 0.010)))
    hair = parsing_masks.get("hair")
    if hair is not None:
        excluded = np.maximum(excluded, hair * 0.95)
    clothes = np.maximum.reduce(
        [
            parsing_masks.get("upper_clothes", np.zeros((height, width), dtype=np.float32)),
            parsing_masks.get("lower_clothes", np.zeros((height, width), dtype=np.float32)),
            parsing_masks.get("dress", np.zeros((height, width), dtype=np.float32)),
        ]
    )
    excluded = np.maximum(excluded, clothes * 0.80)
    return np.clip(excluded, 0, 1).astype(np.float32)


def _luma_rgb(image_rgb: np.ndarray) -> np.ndarray:
    return np.clip(image_rgb[:, :, 0] * 0.299 + image_rgb[:, :, 1] * 0.587 + image_rgb[:, :, 2] * 0.114, 0, 1).astype(np.float32)
