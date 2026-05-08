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
    faces = _detect_skin_regions(image)
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
        bbox = _expand_face_bbox(
            (x_min * width, y_min * height, (x_max - x_min) * width, (y_max - y_min) * height),
            width,
            height,
        )
        faces.append(FaceLandmarks(f"face_{index}", bbox, np.clip(points, -1, 2), 0.98))
    return faces


def _detect_skin_regions(image: np.ndarray) -> list[FaceLandmarks]:
    height, width = image.shape[:2]
    if height < 96 or width < 96 or float(np.std(image)) < 0.035:
        return []

    skin = _skin_mask(image)
    min_dim = min(width, height)
    open_size = max(3, _odd(int(min_dim * 0.006)))
    close_size = max(9, _odd(int(min_dim * 0.022)))
    skin_u8 = (skin.astype(np.uint8) * 255)
    skin_u8 = cv2.morphologyEx(skin_u8, cv2.MORPH_OPEN, np.ones((open_size, open_size), np.uint8))
    skin_u8 = cv2.morphologyEx(skin_u8, cv2.MORPH_CLOSE, np.ones((close_size, close_size), np.uint8))

    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats((skin_u8 > 0).astype(np.uint8), 8)
    image_area = width * height
    candidates: list[tuple[float, tuple[float, float, float, float]]] = []
    for label in range(1, count):
        x, y, candidate_w, candidate_h, area = [int(value) for value in stats[label]]
        score = _score_skin_candidate(x, y, candidate_w, candidate_h, area, width, height, image_area)
        if score <= 0:
            continue
        bbox = _expand_bbox((x, y, candidate_w, candidate_h), width, height)
        candidates.append((score, bbox))

    candidates.sort(key=lambda item: item[0], reverse=True)
    faces: list[FaceLandmarks] = []
    for index, (score, bbox) in enumerate(candidates[:3], start=1):
        faces.append(
            FaceLandmarks(
                f"face_{index}",
                bbox,
                _synthetic_landmarks(bbox, width, height),
                min(0.82, 0.54 + score * 0.06),
            )
        )
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
    detections = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=6, minSize=(48, 48))
    faces: list[FaceLandmarks] = []
    height, width = image.shape[:2]
    skin = _skin_mask(image)
    scored: list[tuple[float, tuple[int, int, int, int]]] = []
    for detection in detections:
        x, y, w, h = [int(value) for value in detection]
        center_y = (y + h * 0.5) / height
        center_x = (x + w * 0.5) / width
        center_bias = 1.0 - min(0.55, abs(center_x - 0.5)) * 0.35
        upper_bias = 1.18 - min(0.70, center_y) * 0.30
        scored.append((float(w * h) * center_bias * upper_bias, (x, y, w, h)))

    for index, (_score, (x, y, w, h)) in enumerate(sorted(scored, key=lambda item: item[0], reverse=True), start=1):
        bbox = _expand_face_bbox((x, y, w, h), width, height)
        if _skin_coverage(skin, bbox) < 0.16:
            continue
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
    bbox = _clamp_bbox(((width - face_w) / 2, height * 0.18, face_w, face_h), width, height)
    return [FaceLandmarks("face_1", bbox, _synthetic_landmarks(bbox, width, height), 0.45)]


def _skin_mask(image: np.ndarray) -> np.ndarray:
    rgb_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    ycrcb = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    balanced_skin = (cr > 130) & (cr < 175) & (cb > 75) & (cb < 140) & (sat > 18) & (sat < 175) & (val > 50)
    warm_skin = ((hue < 18) | (hue > 170)) & (sat > 22) & (sat < 165) & (val > 55) & (cr > 120) & (cb < 150)
    return balanced_skin | warm_skin


def _score_skin_candidate(
    x: int,
    y: int,
    width: int,
    height: int,
    area: int,
    image_width: int,
    image_height: int,
    image_area: int,
) -> float:
    if width <= 0 or height <= 0 or area <= 0:
        return 0.0

    area_ratio = area / image_area
    width_ratio = width / image_width
    height_ratio = height / image_height
    aspect = width / height
    fill = area / (width * height)
    center_y = (y + height * 0.5) / image_height

    if not 0.003 <= area_ratio <= 0.08:
        return 0.0
    if not 0.07 <= width_ratio <= 0.36:
        return 0.0
    if not 0.08 <= height_ratio <= 0.36:
        return 0.0
    if not 0.45 <= aspect <= 1.35:
        return 0.0
    if fill < 0.22:
        return 0.0
    if center_y > 0.58:
        return 0.0

    upper_bonus = 1.25 - center_y
    size_score = min(1.0, area_ratio / 0.018)
    shape_score = 1.0 - min(abs(aspect - 0.78), 0.55)
    fill_score = min(1.0, fill / 0.55)
    return max(0.0, upper_bonus + size_score + shape_score + fill_score)


def _skin_coverage(skin: np.ndarray, bbox: tuple[float, float, float, float]) -> float:
    x, y, w, h = [int(round(value)) for value in bbox]
    x = max(0, min(skin.shape[1] - 1, x))
    y = max(0, min(skin.shape[0] - 1, y))
    x2 = max(x + 1, min(skin.shape[1], x + max(1, w)))
    y2 = max(y + 1, min(skin.shape[0], y + max(1, h)))
    return float(np.mean(skin[y:y2, x:x2]))


def _expand_bbox(
    bbox: tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    pad_x = w * 0.10
    top_pad = h * 0.18
    bottom_pad = h * 0.10
    return _clamp_bbox((x - pad_x, y - top_pad, w + pad_x * 2, h + top_pad + bottom_pad), width, height)


def _expand_face_bbox(
    bbox: tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    pad_x = w * 0.28
    top_pad = h * 0.36
    bottom_pad = h * 0.24
    return _clamp_bbox((x - pad_x, y - top_pad, w + pad_x * 2, h + top_pad + bottom_pad), width, height)


def _clamp_bbox(
    bbox: tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    x1 = float(np.clip(x, 0, max(0, width - 1)))
    y1 = float(np.clip(y, 0, max(0, height - 1)))
    x2 = float(np.clip(x + max(1.0, w), x1 + 1.0, width))
    y2 = float(np.clip(y + max(1.0, h), y1 + 1.0, height))
    return (x1, y1, x2 - x1, y2 - y1)


def _odd(value: int) -> int:
    return value if value % 2 == 1 else value + 1


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
