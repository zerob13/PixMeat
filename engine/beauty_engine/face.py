from __future__ import annotations

import math
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


def detect_faces(
    image: np.ndarray,
    *,
    allow_skin: bool = False,
    allow_heuristic: bool = False,
) -> list[FaceLandmarks]:
    """Detect faces without skin/background guess fallbacks by default."""

    faces = _detect_mediapipe(image)
    if faces:
        return faces
    faces = _detect_eye_pairs(image)
    if faces:
        return faces
    faces = _detect_haar(image)
    if faces:
        return faces
    if allow_skin:
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
    best_confidence = max(face.confidence for face in faces)
    confident = [face for face in faces if face.confidence >= best_confidence - 0.03]
    return max(confident, key=lambda face: face.bbox[2] * face.bbox[3])


def _detect_mediapipe(image: np.ndarray) -> list[FaceLandmarks]:
    try:
        import mediapipe as mp
    except Exception:
        return []
    try:
        face_mesh = mp.solutions.face_mesh.FaceMesh
    except Exception:
        try:
            from mediapipe.python.solutions.face_mesh import FaceMesh

            face_mesh = FaceMesh
        except Exception:
            return []

    rgb_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    height, width = image.shape[:2]
    try:
        with face_mesh(
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


def _detect_eye_pairs(image: np.ndarray) -> list[FaceLandmarks]:
    rgb_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    height, width = image.shape[:2]
    skin = _skin_mask(image)
    eyes = _eye_candidates(gray, width, height)
    if len(eyes) < 2:
        return []

    scored: list[tuple[float, FaceLandmarks]] = []
    for left_index, left in enumerate(eyes):
        for right in eyes[left_index + 1 :]:
            candidate = _face_from_eye_pair(left, right, width, height)
            if candidate is None:
                continue
            score = _score_eye_pair_face(gray, skin, candidate.bbox)
            if score < 2.80:
                continue
            confidence = float(np.clip(0.52 + score * 0.075, 0.62, 0.90))
            scored.append(
                (
                    score,
                    FaceLandmarks(
                        f"face_{len(scored) + 1}",
                        candidate.bbox,
                        candidate.points,
                        confidence,
                    ),
                )
            )

    if scored:
        top_score = max(score for score, _face in scored)
        scored = [(score, face) for score, face in scored if score >= top_score - 0.35]
    return _dedupe_scored_faces(scored, width, height, limit=3)


def _eye_candidates(gray: np.ndarray, width: int, height: int) -> list[tuple[float, float, float]]:
    detections: list[tuple[float, float, float]] = []
    max_eye = max(18, int(round(width * 0.085)))
    for cascade_name in ("haarcascade_eye_tree_eyeglasses.xml", "haarcascade_eye.xml"):
        cascade_path = cv2.data.haarcascades + cascade_name
        if not Path(cascade_path).exists():
            continue
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            continue
        boxes = cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(12, 12),
            maxSize=(max_eye, max_eye),
        )
        for x, y, candidate_w, candidate_h in boxes:
            size = float((candidate_w + candidate_h) * 0.5)
            center_x = float(x + candidate_w * 0.5)
            center_y = float(y + candidate_h * 0.5)
            if not 0.06 <= center_x / width <= 0.94:
                continue
            if not 0.12 <= center_y / height <= 0.66:
                continue
            detections.append((center_x, center_y, size))
    return _dedupe_eye_candidates(detections)


def _dedupe_eye_candidates(candidates: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    candidates = sorted(candidates, key=lambda item: item[2], reverse=True)
    kept: list[tuple[float, float, float]] = []
    for candidate in candidates:
        cx, cy, size = candidate
        if any(math.hypot(cx - kx, cy - ky) < max(size, ksize) * 0.55 for kx, ky, ksize in kept):
            continue
        kept.append(candidate)
    return kept[:48]


def _face_from_eye_pair(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    width: int,
    height: int,
) -> FaceLandmarks | None:
    ax, ay, a_size = first
    bx, by, b_size = second
    if ax > bx:
        ax, ay, a_size, bx, by, b_size = bx, by, b_size, ax, ay, a_size

    dx = bx - ax
    dy = by - ay
    distance = math.hypot(dx, dy)
    average_size = (a_size + b_size) * 0.5
    if distance < max(width * 0.035, average_size * 1.45) or distance > width * 0.24:
        return None
    if abs(dy) > distance * 0.72:
        return None
    if max(a_size, b_size) / max(1.0, min(a_size, b_size)) > 1.9:
        return None
    roll = math.atan2(dy, dx)
    if abs(math.degrees(roll)) > 42:
        return None

    direction = np.array([dx, dy], dtype=np.float32) / max(distance, 1.0)
    down = np.array([-direction[1], direction[0]], dtype=np.float32)
    if down[1] < 0:
        down *= -1
    midpoint = np.array([(ax + bx) * 0.5, (ay + by) * 0.5], dtype=np.float32)
    face_w = float(distance / 0.32)
    face_h = float(distance * 3.35)
    center = midpoint + down * np.float32(face_h * 0.08)
    bbox = _clamp_bbox(
        (
            float(center[0] - face_w * 0.50),
            float(center[1] - face_h * 0.50),
            face_w,
            face_h,
        ),
        width,
        height,
    )
    if bbox[2] / width > 0.34 or bbox[3] / height > 0.36:
        return None
    points = _synthetic_landmarks(bbox, width, height, roll=roll)
    return FaceLandmarks("face_1", bbox, points, 0.0)


def _score_eye_pair_face(gray: np.ndarray, skin: np.ndarray, bbox: tuple[float, float, float, float]) -> float:
    height, width = gray.shape[:2]
    x, y, w, h = [int(round(value)) for value in bbox]
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    x2 = max(x + 1, min(width, x + max(1, w)))
    y2 = max(y + 1, min(height, y + max(1, h)))
    roi = gray[y:y2, x:x2]
    if roi.size == 0:
        return 0.0

    skin_coverage = float(np.mean(skin[y:y2, x:x2]))
    dark_ratio = float(np.mean(roi < 65))
    edge_ratio = float(np.mean(cv2.Canny(roi, 60, 140) > 0))
    center_x = (x + (x2 - x) * 0.5) / width
    center_y = (y + (y2 - y) * 0.5) / height
    center_bias = 1.0 - min(1.0, abs(center_x - 0.48) * 1.2)
    vertical_bias = 1.0 - min(1.0, abs(center_y - 0.34) * 1.5)
    size_ratio = ((x2 - x) * (y2 - y)) / max(1, width * height)
    size_score = min(1.0, size_ratio / 0.035)

    score = skin_coverage * 2.8 + dark_ratio * 1.4 + edge_ratio + center_bias + vertical_bias + size_score
    if skin_coverage < 0.12:
        score -= 1.25
    if dark_ratio < 0.04:
        score -= 1.10
    return float(score)


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
    gray = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    candidates: list[tuple[float, tuple[float, float, float, float], bool]] = []
    for label in range(1, count):
        x, y, candidate_w, candidate_h, area = [int(value) for value in stats[label]]
        score = _score_skin_candidate(x, y, candidate_w, candidate_h, area, width, height, image_area)
        wide_score = _score_wide_skin_candidate(gray, skin, x, y, candidate_w, candidate_h, area)
        if score <= 0 and wide_score <= 0:
            continue
        use_wide = wide_score > score
        bbox = (
            _bbox_from_wide_skin_candidate(_centroids[label], x, y, candidate_w, candidate_h, width, height)
            if use_wide
            else _expand_bbox((x, y, candidate_w, candidate_h), width, height)
        )
        candidates.append((max(score, wide_score), bbox, use_wide))

    candidates.sort(key=lambda item: item[0], reverse=True)
    scored_faces: list[tuple[float, FaceLandmarks]] = []
    for index, (score, bbox, _use_wide) in enumerate(candidates[:8], start=1):
        scored_faces.append(
            (
                score,
                FaceLandmarks(
                    f"face_{index}",
                    bbox,
                    _synthetic_landmarks(bbox, width, height),
                    min(0.82, 0.54 + score * 0.06),
                ),
            )
        )
    return _dedupe_scored_faces(scored_faces, width, height, limit=3)


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

    faces: list[tuple[float, FaceLandmarks]] = []
    for index, (_score, (x, y, w, h)) in enumerate(sorted(scored, key=lambda item: item[0], reverse=True), start=1):
        bbox = _expand_face_bbox((x, y, w, h), width, height)
        quality = _score_haar_face(gray, skin, bbox)
        if quality < 1.20:
            continue
        faces.append((_score * quality, FaceLandmarks(f"face_{index}", bbox, _synthetic_landmarks(bbox, width, height), 0.72)))
    return _dedupe_scored_faces(faces, width, height, limit=3)


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


def _score_haar_face(gray: np.ndarray, skin: np.ndarray, bbox: tuple[float, float, float, float]) -> float:
    height, width = gray.shape[:2]
    x, y, w, h = [int(round(value)) for value in bbox]
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    x2 = max(x + 1, min(width, x + max(1, w)))
    y2 = max(y + 1, min(height, y + max(1, h)))
    roi = gray[y:y2, x:x2]
    if roi.size == 0:
        return 0.0
    skin_coverage = float(np.mean(skin[y:y2, x:x2]))
    dark_ratio = float(np.mean(roi < 62))
    center_y = (y + (y2 - y) * 0.5) / height
    center_x = (x + (x2 - x) * 0.5) / width
    center_bias = 1.0 - min(1.0, abs(center_x - 0.5) * 1.1)
    return skin_coverage * 2.0 + dark_ratio * 1.2 + center_bias * 0.6 + max(0.0, 0.55 - center_y)


def _score_wide_skin_candidate(
    gray: np.ndarray,
    skin: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    area: int,
) -> float:
    image_height, image_width = gray.shape[:2]
    if width <= 0 or height <= 0 or area <= 0:
        return 0.0
    area_ratio = area / max(1, image_width * image_height)
    width_ratio = width / image_width
    height_ratio = height / image_height
    aspect = width / max(1, height)
    center_x = (x + width * 0.5) / image_width
    center_y = (y + height * 0.5) / image_height
    if not 0.006 <= area_ratio <= 0.040:
        return 0.0
    if not 0.12 <= width_ratio <= 0.42:
        return 0.0
    if not 0.055 <= height_ratio <= 0.18:
        return 0.0
    if not 1.25 <= aspect <= 2.95:
        return 0.0
    if not 0.18 <= center_x <= 0.78:
        return 0.0
    if not 0.19 <= center_y <= 0.46:
        return 0.0

    x2 = min(image_width, x + width)
    y2 = min(image_height, y + height)
    roi = gray[y:y2, x:x2]
    if roi.size == 0:
        return 0.0
    dark_ratio = float(np.mean(roi < 65))
    skin_coverage = float(np.mean(skin[y:y2, x:x2]))
    if skin_coverage < 0.22 or dark_ratio < 0.08:
        return 0.0
    center_bias = 1.0 - min(1.0, abs(center_x - 0.48) * 1.6)
    vertical_bias = 1.0 - min(1.0, abs(center_y - 0.33) * 2.0)
    size_score = min(1.0, area_ratio / 0.018)
    return max(0.0, 1.2 + center_bias + vertical_bias + size_score + dark_ratio * 1.4)


def _bbox_from_wide_skin_candidate(
    centroid: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    center_x = float(centroid[0])
    center_y = float(centroid[1])
    face_w = float(np.clip(min(width * 0.66, height * 1.44), image_width * 0.12, image_width * 0.23))
    face_h = face_w * 1.05
    return _clamp_bbox((center_x - face_w * 0.52, center_y - face_h * 0.48, face_w, face_h), image_width, image_height)


def _dedupe_scored_faces(
    scored: list[tuple[float, FaceLandmarks]],
    width: int,
    height: int,
    *,
    limit: int,
) -> list[FaceLandmarks]:
    faces: list[FaceLandmarks] = []
    for _score, face in sorted(scored, key=lambda item: item[0], reverse=True):
        x, y, w, h = face.bbox
        center = np.array([x + w * 0.5, y + h * 0.5], dtype=np.float32)
        if any(
            np.linalg.norm(
                center
                - np.array(
                    [other.bbox[0] + other.bbox[2] * 0.5, other.bbox[1] + other.bbox[3] * 0.5],
                    dtype=np.float32,
                )
            )
            < max(w, h, other.bbox[2], other.bbox[3]) * 0.42
            for other in faces
        ):
            continue
        faces.append(FaceLandmarks(f"face_{len(faces) + 1}", face.bbox, face.points, face.confidence))
        if len(faces) >= limit:
            break
    return faces


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
    bbox: tuple[float, float, float, float], width: int, height: int, *, roll: float = 0.0
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
    if abs(roll) > 1e-3:
        _rotate_points(points, center, roll, width, height)
    return points


def _rotate_points(points: np.ndarray, center: np.ndarray, roll: float, width: int, height: int) -> None:
    pixel_points = points[:, :2].copy()
    pixel_points[:, 0] *= width
    pixel_points[:, 1] *= height
    cos_a = math.cos(roll)
    sin_a = math.sin(roll)
    delta = pixel_points - center.reshape(1, 2)
    rotated = np.empty_like(delta)
    rotated[:, 0] = delta[:, 0] * cos_a - delta[:, 1] * sin_a
    rotated[:, 1] = delta[:, 0] * sin_a + delta[:, 1] * cos_a
    rotated += center.reshape(1, 2)
    points[:, 0] = np.clip(rotated[:, 0] / width, -1.0, 2.0)
    points[:, 1] = np.clip(rotated[:, 1] / height, -1.0, 2.0)


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
