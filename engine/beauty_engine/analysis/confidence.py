from __future__ import annotations

import math

import numpy as np

from beauty_engine import landmark_indices as idx
from beauty_engine.types import AnalysisConfidence, BBox, FaceQuality


def score_face_bbox(bbox: BBox, image_size: tuple[int, int], confidence: float) -> float:
    """Score faces by area, centrality, and detector confidence."""

    width, height = image_size
    x, y, w, h = bbox
    area_ratio = (w * h) / max(1.0, width * height)
    cx = (x + w * 0.5) / max(1, width)
    cy = (y + h * 0.5) / max(1, height)
    centrality = 1.0 - min(1.0, math.hypot(cx - 0.5, cy - 0.40) * 1.5)
    return float(area_ratio * 4.0 + centrality * 0.75 + confidence * 0.85)


def estimate_face_quality(
    landmarks: np.ndarray | None,
    bbox: BBox,
    image_size: tuple[int, int],
    confidence: float,
) -> FaceQuality:
    """Estimate basic quality hints from landmark geometry."""

    width, height = image_size
    _x, _y, w, h = bbox
    face_size_ratio = float((w * h) / max(1.0, width * height))
    yaw_hint = 0.0
    pitch_hint = 0.0
    roll_hint = 0.0
    if landmarks is not None and landmarks.shape[0] > max(idx.RIGHT_EYE + idx.LEFT_EYE):
        left_eye = np.mean(landmarks[idx.LEFT_EYE, :2], axis=0)
        right_eye = np.mean(landmarks[idx.RIGHT_EYE, :2], axis=0)
        eye_delta = right_eye - left_eye
        roll_hint = float(math.degrees(math.atan2(float(eye_delta[1]), float(eye_delta[0]))))
        nose = np.mean(landmarks[idx.NOSE_TIP, :2], axis=0)
        mouth = np.mean(landmarks[idx.OUTER_LIPS, :2], axis=0)
        face_center_x = (left_eye[0] + right_eye[0] + nose[0] + mouth[0]) / 4.0
        yaw_hint = float(np.clip((nose[0] - face_center_x) / max(w * 0.12, 1.0), -1, 1))
        pitch_hint = float(np.clip((nose[1] - (left_eye[1] + right_eye[1]) * 0.5) / max(h * 0.30, 1.0), -1, 1))
    landmark_confidence = float(np.clip(confidence, 0, 1))
    is_profile = abs(yaw_hint) > 0.60 or abs(roll_hint) > 38.0
    unavailable: list[str] = []
    if is_profile or face_size_ratio < 0.004 or landmark_confidence < 0.45:
        unavailable.extend(["face_slim", "jawline", "nose_slim"])
    if landmark_confidence < 0.35:
        unavailable.extend(["eye_enlarge", "smile"])
    return FaceQuality(
        face_size_ratio=face_size_ratio,
        landmark_confidence=landmark_confidence,
        yaw_hint=yaw_hint,
        pitch_hint=pitch_hint,
        roll_hint=roll_hint,
        is_profile_hint=is_profile,
        unavailable_sliders=sorted(set(unavailable)),
    )


def aggregate_confidence(
    face_detection: float,
    face_landmarks: float,
    person_segmentation: float,
    human_parsing: float,
    skin_mask: float,
) -> AnalysisConfidence:
    values = [face_detection, face_landmarks, person_segmentation, human_parsing, skin_mask]
    overall = float(np.clip(np.mean(values), 0, 1))
    return AnalysisConfidence(
        face_detection=float(np.clip(face_detection, 0, 1)),
        face_landmarks=float(np.clip(face_landmarks, 0, 1)),
        person_segmentation=float(np.clip(person_segmentation, 0, 1)),
        human_parsing=float(np.clip(human_parsing, 0, 1)),
        skin_mask=float(np.clip(skin_mask, 0, 1)),
        overall=overall,
    )
