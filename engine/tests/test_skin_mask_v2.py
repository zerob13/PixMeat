from __future__ import annotations

import cv2
import numpy as np

from beauty_engine import landmark_indices as idx
from beauty_engine.analysis.skin_mask import build_skin_masks_v2
from beauty_engine.face import _synthetic_landmarks
from beauty_engine.masks import polygon_mask
from beauty_engine.types import FaceResult, expand_bbox


def test_skin_mask_v2_excludes_protected_face_regions() -> None:
    height, width = 180, 140
    image_bgr = np.zeros((height, width, 3), dtype=np.uint8)
    image_bgr[:, :] = (52, 58, 64)
    bbox = (34.0, 24.0, 72.0, 112.0)
    landmarks = _synthetic_landmarks(bbox, width, height)
    points = landmarks.copy()
    points[:, 0] *= width
    points[:, 1] *= height

    cv2.ellipse(image_bgr, (70, 82), (34, 52), 0, 0, 360, (118, 158, 210), -1)
    left_eye = np.mean(points[idx.LEFT_EYE, :2], axis=0).astype(int)
    mouth = np.mean(points[idx.OUTER_LIPS, :2], axis=0).astype(int)
    cv2.ellipse(image_bgr, tuple(left_eye), (7, 4), 0, 0, 360, (20, 20, 20), -1)
    cv2.ellipse(image_bgr, tuple(mouth), (16, 5), 0, 0, 360, (28, 26, 90), -1)

    face = FaceResult(
        face_id="face_1",
        bbox=bbox,
        expanded_bbox=expand_bbox(bbox, 1.35, width, height),
        score=1.0,
        confidence=0.9,
        source="test",
        landmarks=points,
    )
    person_mask = np.ones((height, width), dtype=np.float32)
    face_mask = polygon_mask((height, width), points[idx.FACE_OVAL, :2])
    parsing_masks = {
        "face": face_mask,
        "neck": np.zeros((height, width), dtype=np.float32),
        "left_arm": np.zeros((height, width), dtype=np.float32),
        "right_arm": np.zeros((height, width), dtype=np.float32),
        "skin": face_mask,
        "hair": np.zeros((height, width), dtype=np.float32),
        "upper_clothes": np.zeros((height, width), dtype=np.float32),
        "lower_clothes": np.zeros((height, width), dtype=np.float32),
        "dress": np.zeros((height, width), dtype=np.float32),
    }

    masks, confidence = build_skin_masks_v2(image_bgr, person_mask, parsing_masks, [face])
    cheek = masks["skin_final_mask"][82, 70]
    eye_value = masks["skin_final_mask"][left_eye[1], left_eye[0]]
    mouth_value = masks["skin_final_mask"][mouth[1], mouth[0]]

    assert confidence >= 0.70
    assert cheek > 0.35
    assert eye_value < cheek * 0.50
    assert mouth_value < cheek * 0.50
    assert masks["skin_exclusion_mask"][left_eye[1], left_eye[0]] > 0.4
