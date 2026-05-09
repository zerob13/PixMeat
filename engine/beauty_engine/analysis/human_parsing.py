from __future__ import annotations

import cv2
import numpy as np

from beauty_engine import landmark_indices as idx
from beauty_engine.masks import polygon_mask
from beauty_engine.types import FaceResult, PersonResult

from .model_registry import ModelRegistry

PARSING_LABELS = {
    "background",
    "face",
    "hair",
    "neck",
    "upper_clothes",
    "lower_clothes",
    "dress",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
    "left_shoe",
    "right_shoe",
    "torso",
    "skin",
}


class HumanParserV2:
    """Human parsing wrapper with documented coarse fallback regions."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def parse(
        self,
        image_bgr: np.ndarray,
        person_mask: np.ndarray,
        faces: list[FaceResult],
        persons: list[PersonResult],
    ) -> tuple[dict[str, np.ndarray], float, str]:
        loaded = self.registry.get_human_parser()
        if loaded.model is not None:
            self.registry.backend_info["human_parsing"] = loaded.info.__class__(
                loaded.info.name,
                loaded.info.backend,
                loaded.info.provider,
                loaded.info.model_path,
                False,
                "fallback",
                "Generic SCHP/CIHP/LIP/ATR adapter is not configured",
                loaded.info.elapsed_ms,
            )
        masks = coarse_human_parsing(image_bgr.shape[:2], person_mask, faces, persons)
        return masks, 0.36 if faces and persons else 0.20, "geometric_fallback"


def coarse_human_parsing(
    shape: tuple[int, int],
    person_mask: np.ndarray,
    faces: list[FaceResult],
    persons: list[PersonResult],
) -> dict[str, np.ndarray]:
    height, width = shape
    masks = {label: np.zeros((height, width), dtype=np.float32) for label in PARSING_LABELS}
    masks["background"] = np.clip(1.0 - person_mask, 0, 1).astype(np.float32)
    if not persons:
        return masks

    person_bbox = persons[0].bbox
    px, py, pw, ph = person_bbox
    face = faces[0] if faces else None
    if face is not None:
        face_mask = _face_mask_from_landmarks(shape, face)
        masks["face"] = np.minimum(face_mask, person_mask)
        x, y, face_w, face_h = face.bbox
        hair = np.zeros((height, width), dtype=np.float32)
        cv2.ellipse(
            hair,
            (int(x + face_w * 0.50), int(y + face_h * 0.22)),
            (max(2, int(face_w * 0.58)), max(2, int(face_h * 0.38))),
            0,
            180,
            360,
            1.0,
            -1,
        )
        masks["hair"] = np.minimum(cv2.GaussianBlur(hair, (0, 0), sigmaX=max(1.0, face_w * 0.018)), person_mask)
        neck = np.zeros((height, width), dtype=np.float32)
        cv2.rectangle(
            neck,
            (int(x + face_w * 0.30), int(y + face_h * 0.82)),
            (int(x + face_w * 0.70), int(y + face_h * 1.38)),
            1.0,
            -1,
        )
        masks["neck"] = np.minimum(cv2.GaussianBlur(neck, (0, 0), sigmaX=max(1.0, face_w * 0.025)), person_mask)
        torso_top = y + face_h * 1.18
        torso_center_x = x + face_w * 0.5
        body_unit = face_w
    else:
        torso_top = py + ph * 0.18
        torso_center_x = px + pw * 0.5
        body_unit = max(24.0, pw * 0.22)

    torso = np.zeros((height, width), dtype=np.float32)
    torso_bottom = min(height - 1, int(torso_top + max(body_unit * 3.2, ph * 0.42)))
    cv2.ellipse(
        torso,
        (int(torso_center_x), int((torso_top + torso_bottom) * 0.5)),
        (int(body_unit * 1.55), int(max(8.0, (torso_bottom - torso_top) * 0.52))),
        0,
        0,
        360,
        1.0,
        -1,
    )
    torso = np.minimum(cv2.GaussianBlur(torso, (0, 0), sigmaX=max(1.0, body_unit * 0.035)), person_mask)
    masks["torso"] = torso
    masks["upper_clothes"] = torso
    lower = np.zeros((height, width), dtype=np.float32)
    cv2.rectangle(lower, (int(px), int(torso_bottom)), (int(px + pw), int(py + ph)), 1.0, -1)
    masks["lower_clothes"] = np.minimum(cv2.GaussianBlur(lower, (0, 0), sigmaX=max(1.0, body_unit * 0.025)), person_mask)

    yy, xx = np.mgrid[:height, :width].astype(np.float32)
    left_side = xx < torso_center_x - body_unit * 0.95
    right_side = xx > torso_center_x + body_unit * 0.95
    arm_vertical = (yy > torso_top) & (yy < min(height, py + ph * 0.92))
    masks["left_arm"] = np.where(left_side & arm_vertical, person_mask, 0).astype(np.float32)
    masks["right_arm"] = np.where(right_side & arm_vertical, person_mask, 0).astype(np.float32)
    lower_body = (yy >= torso_bottom) & (yy < py + ph)
    masks["left_leg"] = np.where((xx < torso_center_x) & lower_body, person_mask, 0).astype(np.float32)
    masks["right_leg"] = np.where((xx >= torso_center_x) & lower_body, person_mask, 0).astype(np.float32)
    masks["skin"] = np.clip(masks["face"] + masks["neck"] + masks["left_arm"] + masks["right_arm"], 0, 1)
    return {name: np.clip(mask, 0, 1).astype(np.float32) for name, mask in masks.items()}


def _face_mask_from_landmarks(shape: tuple[int, int], face: FaceResult) -> np.ndarray:
    height, width = shape
    if face.landmarks is not None and face.landmarks.shape[0] > max(idx.FACE_OVAL):
        mask = polygon_mask((height, width), face.landmarks[idx.FACE_OVAL, :2])
        return cv2.GaussianBlur(mask, (0, 0), sigmaX=max(1.0, face.bbox[2] * 0.018)).astype(np.float32)
    x, y, w, h = face.bbox
    mask = np.zeros((height, width), dtype=np.float32)
    cv2.ellipse(mask, (int(x + w * 0.5), int(y + h * 0.53)), (int(w * 0.46), int(h * 0.50)), 0, 0, 360, 1.0, -1)
    return cv2.GaussianBlur(mask, (0, 0), sigmaX=max(1.0, w * 0.018)).astype(np.float32)
