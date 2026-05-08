from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from . import landmark_indices as idx


@dataclass(frozen=True)
class FaceLandmarks:
    face_id: str
    bbox: tuple[float, float, float, float]
    points: np.ndarray
    confidence: float

    def to_json(self) -> dict[str, object]:
        return {
            "face_id": self.face_id,
            "bbox": [float(v) for v in self.bbox],
            "confidence": float(self.confidence),
            "landmark_count": int(self.points.shape[0]),
        }

    def points_px(self, width: int, height: int) -> np.ndarray:
        points = self.points.copy()
        points[:, 0] *= width
        points[:, 1] *= height
        return points


def detect_faces(image: np.ndarray, allow_heuristic: bool = True) -> list[FaceLandmarks]:
    faces = _detect_mediapipe(image)
    if faces:
        return faces
    faces = _detect_haar(image)
    if faces:
        return faces
    if allow_heuristic:
        heuristic = _detect_heuristic(image)
        if heuristic:
            return heuristic
    return []


def serialize_faces(faces: Iterable[FaceLandmarks]) -> list[dict[str, object]]:
    return [face.to_json() for face in faces]


def find_face(faces: list[FaceLandmarks], face_id: str | None) -> FaceLandmarks | None:
    if not faces:
        return None
    if face_id:
        for face in faces:
            if face.face_id == face_id:
                return face
    return max(faces, key=lambda face: face.bbox[2] * face.bbox[3])


def _detect_mediapipe(image: np.ndarray) -> list[FaceLandmarks]:
    try:
        import mediapipe as mp
    except Exception:
        return []

    rgb_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    height, width = image.shape[:2]
    try:
        with mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=8,
            refine_landmarks=True,
            min_detection_confidence=0.45,
        ) as mesh:
            result = mesh.process(rgb_u8)
    except Exception:
        return []

    faces: list[FaceLandmarks] = []
    for index, landmarks in enumerate(result.multi_face_landmarks or [], start=1):
        points = np.array([[lm.x, lm.y, lm.z] for lm in landmarks.landmark], dtype=np.float32)
        x_min, y_min = np.min(points[:, :2], axis=0)
        x_max, y_max = np.max(points[:, :2], axis=0)
        bbox = (x_min * width, y_min * height, (x_max - x_min) * width, (y_max - y_min) * height)
        faces.append(FaceLandmarks(f"face_{index}", bbox, np.clip(points, -1, 2), 0.98))
    return faces


def _detect_haar(image: np.ndarray) -> list[FaceLandmarks]:
    rgb_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if not Path(cascade_path).exists():
        return []
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        return []
    detections = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(48, 48))
    faces: list[FaceLandmarks] = []
    height, width = image.shape[:2]
    for index, (x, y, w, h) in enumerate(sorted(detections, key=lambda item: item[2] * item[3], reverse=True), start=1):
        pad_x = int(w * 0.14)
        pad_y = int(h * 0.18)
        bbox = (
            max(0, x - pad_x),
            max(0, y - pad_y),
            min(width - max(0, x - pad_x), w + pad_x * 2),
            min(height - max(0, y - pad_y), h + pad_y * 2),
        )
        faces.append(FaceLandmarks(f"face_{index}", bbox, _synthetic_landmarks(bbox, width, height), 0.72))
    return faces


def _detect_heuristic(image: np.ndarray) -> list[FaceLandmarks]:
    height, width = image.shape[:2]
    if float(np.std(image)) < 0.045:
        return []

    hsv = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    skin = ((hue < 25) | (hue > 165)) & (sat > 25) & (sat < 180) & (val > 55)
    score = float(np.mean(skin))
    if score < 0.015:
        return []

    face_w = width * 0.34
    face_h = min(height * 0.62, face_w * 1.35)
    bbox = ((width - face_w) / 2, height * 0.18, face_w, face_h)
    return [FaceLandmarks("face_1", bbox, _synthetic_landmarks(bbox, width, height), 0.45)]


def _synthetic_landmarks(
    bbox: tuple[float, float, float, float], width: int, height: int
) -> np.ndarray:
    x, y, w, h = bbox
    points = np.zeros((468, 3), dtype=np.float32)
    center = np.array([x + w * 0.5, y + h * 0.5], dtype=np.float32)
    points[:, 0] = center[0] / width
    points[:, 1] = center[1] / height

    _place_ellipse(points, idx.FACE_OVAL, center, w * 0.52, h * 0.54, width, height, start=-90, end=270)
    _place_ellipse(points, idx.LEFT_EYE, (x + w * 0.34, y + h * 0.42), w * 0.105, h * 0.045, width, height)
    _place_ellipse(points, idx.RIGHT_EYE, (x + w * 0.66, y + h * 0.42), w * 0.105, h * 0.045, width, height)
    _place_arc(points, idx.LEFT_EYEBROW, (x + w * 0.34, y + h * 0.34), w * 0.13, h * 0.035, width, height)
    _place_arc(points, idx.RIGHT_EYEBROW, (x + w * 0.66, y + h * 0.34), w * 0.13, h * 0.035, width, height)
    _place_ellipse(points, idx.OUTER_LIPS, (x + w * 0.5, y + h * 0.70), w * 0.17, h * 0.055, width, height)
    _place_ellipse(points, idx.INNER_LIPS, (x + w * 0.5, y + h * 0.70), w * 0.105, h * 0.028, width, height)
    _place_line(points, idx.NOSE_BRIDGE, (x + w * 0.50, y + h * 0.43), (x + w * 0.50, y + h * 0.62), width, height)
    _place_ellipse(points, idx.NOSE_LEFT + idx.NOSE_RIGHT, (x + w * 0.5, y + h * 0.60), w * 0.095, h * 0.035, width, height)
    _place_arc(points, idx.CHIN, (x + w * 0.5, y + h * 0.88), w * 0.12, h * 0.06, width, height, start=20, end=160)
    _place_line(points, idx.LEFT_JAW, (x + w * 0.08, y + h * 0.52), (x + w * 0.38, y + h * 0.93), width, height)
    _place_line(points, idx.RIGHT_JAW, (x + w * 0.92, y + h * 0.52), (x + w * 0.62, y + h * 0.93), width, height)
    return points


def _place_ellipse(
    points: np.ndarray,
    indices: list[int],
    center_xy: tuple[float, float] | np.ndarray,
    radius_x: float,
    radius_y: float,
    width: int,
    height: int,
    start: float = 0,
    end: float = 360,
) -> None:
    cx, cy = center_xy
    angles = np.deg2rad(np.linspace(start, end, len(indices), endpoint=False))
    for landmark_index, angle in zip(indices, angles):
        points[landmark_index, 0] = (cx + np.cos(angle) * radius_x) / width
        points[landmark_index, 1] = (cy + np.sin(angle) * radius_y) / height


def _place_arc(
    points: np.ndarray,
    indices: list[int],
    center_xy: tuple[float, float],
    radius_x: float,
    radius_y: float,
    width: int,
    height: int,
    start: float = 200,
    end: float = 340,
) -> None:
    _place_ellipse(points, indices, center_xy, radius_x, radius_y, width, height, start=start, end=end)


def _place_line(
    points: np.ndarray,
    indices: list[int],
    start_xy: tuple[float, float],
    end_xy: tuple[float, float],
    width: int,
    height: int,
) -> None:
    xs = np.linspace(start_xy[0], end_xy[0], len(indices))
    ys = np.linspace(start_xy[1], end_xy[1], len(indices))
    for landmark_index, px, py in zip(indices, xs, ys):
        points[landmark_index, 0] = px / width
        points[landmark_index, 1] = py / height
