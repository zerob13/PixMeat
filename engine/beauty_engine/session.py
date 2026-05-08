from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .face import FaceLandmarks, detect_faces, serialize_faces
from .io import ImageData, read_image, resize_max_side, write_image, write_json
from .landmark_indices import FACE_OVAL


@dataclass
class ImageSession:
    image_id: str
    source_path: str
    cache_dir: Path
    width: int
    height: int
    preview_width: int
    preview_height: int
    preview_path: Path
    faces: list[FaceLandmarks]
    active_face_id: str | None
    exif: bytes | None = None
    alpha: np.ndarray | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "image_id": self.image_id,
            "source_path": self.source_path,
            "preview_path": str(self.preview_path),
            "width": self.width,
            "height": self.height,
            "preview_width": self.preview_width,
            "preview_height": self.preview_height,
            "faces": serialize_faces(self.faces_for_size(self.preview_width, self.preview_height)),
            "active_face_id": self.active_face_id,
        }

    def faces_for_size(self, width: int, height: int) -> list[FaceLandmarks]:
        return [scale_face(face, width, height) for face in self.faces]


class SessionRegistry:
    def __init__(self, cache_root: str | Path | None = None) -> None:
        self.cache_root = Path(cache_root) if cache_root else default_cache_root()
        self.sessions: dict[str, ImageSession] = {}

    def load_image(self, image_path: str, preview_max_side: int = 1600, detect: bool = True) -> ImageSession:
        data = read_image(image_path)
        preview = resize_max_side(data.rgb, int(np.clip(preview_max_side, 512, 2400)))
        preview_height, preview_width = preview.shape[:2]
        image_id = f"img_{int(time.time() * 1000)}_{len(self.sessions) + 1}"
        cache_dir = self.cache_root / "sessions" / image_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        preview_path = cache_dir / "preview.png"
        write_image(preview_path, preview)

        preview_faces = detect_faces(preview) if detect else []
        faces = normalize_faces(preview_faces, preview_width, preview_height)
        active = max(faces, key=lambda item: item.bbox[2] * item.bbox[3]).face_id if faces else None

        session = ImageSession(
            image_id=image_id,
            source_path=str(Path(image_path)),
            cache_dir=cache_dir,
            width=data.width,
            height=data.height,
            preview_width=preview_width,
            preview_height=preview_height,
            preview_path=preview_path,
            faces=faces,
            active_face_id=active,
            exif=data.exif,
            alpha=data.alpha,
        )
        self.sessions[image_id] = session
        write_json(cache_dir / "session.json", session.to_json())
        return session

    def get(self, image_id: str) -> ImageSession | None:
        return self.sessions.get(image_id)


def default_cache_root() -> Path:
    env_path = os.environ.get("PIXMEAT_CACHE_DIR")
    if env_path:
        return Path(env_path)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        return Path(base) / "PixMeat" / "Cache"
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Caches" / "PixMeat"
    return Path(tempfile.gettempdir()) / "PixMeat" / "Cache"


def sys_platform() -> str:
    import sys

    return sys.platform


def normalize_faces(faces: list[FaceLandmarks], width: int, height: int) -> list[FaceLandmarks]:
    normalized: list[FaceLandmarks] = []
    for face in faces:
        x, y, w, h = face.bbox
        bbox = (x / width, y / height, w / width, h / height)
        normalized.append(FaceLandmarks(face.face_id, bbox, face.points.copy(), face.confidence))
    return normalized


def scale_face(face: FaceLandmarks, width: int, height: int) -> FaceLandmarks:
    points = face.points.copy()
    oval = points[FACE_OVAL, :2]
    x_min, y_min = np.min(oval, axis=0)
    x_max, y_max = np.max(oval, axis=0)
    if x_max <= x_min or y_max <= y_min:
        x, y, w, h = face.bbox
        bbox = (x * width, y * height, w * width, h * height)
    else:
        bbox = (x_min * width, y_min * height, (x_max - x_min) * width, (y_max - y_min) * height)
    return FaceLandmarks(face.face_id, clamp_bbox(bbox, width, height), points, face.confidence)


def clamp_bbox(bbox: tuple[float, float, float, float], width: int, height: int) -> tuple[float, float, float, float]:
    x, y, w, h = bbox
    x1 = float(np.clip(x, 0, max(0, width - 1)))
    y1 = float(np.clip(y, 0, max(0, height - 1)))
    x2 = float(np.clip(x + max(1.0, w), x1 + 1.0, width))
    y2 = float(np.clip(y + max(1.0, h), y1 + 1.0, height))
    return (x1, y1, x2 - x1, y2 - y1)


def read_session_image(session: ImageSession, preview: bool) -> ImageData:
    return read_image(session.preview_path if preview else session.source_path)
