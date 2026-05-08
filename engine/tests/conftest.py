from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from beauty_engine.face import FaceLandmarks


@pytest.fixture()
def portrait_image() -> np.ndarray:
    return make_portrait()


@pytest.fixture()
def portrait_face(portrait_image: np.ndarray) -> FaceLandmarks:
    height, width = portrait_image.shape[:2]
    from beauty_engine.face import _synthetic_landmarks

    bbox = (width * 0.31, height * 0.16, width * 0.38, height * 0.68)
    return FaceLandmarks("face_1", bbox, _synthetic_landmarks(bbox, width, height), 0.9)


def make_portrait(width: int = 220, height: int = 280) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.float32)
    image[:, :, 0] = 0.22
    image[:, :, 1] = 0.24
    image[:, :, 2] = 0.28
    center = (width // 2, int(height * 0.48))
    axes = (int(width * 0.22), int(height * 0.31))
    cv2.ellipse(image, center, axes, 0, 0, 360, (0.82, 0.58, 0.46), -1)
    cv2.ellipse(image, (center[0], int(height * 0.25)), (int(width * 0.24), int(height * 0.11)), 0, 0, 360, (0.12, 0.10, 0.08), -1)
    cv2.ellipse(image, (int(width * 0.42), int(height * 0.43)), (10, 5), 0, 0, 360, (0.95, 0.95, 0.90), -1)
    cv2.ellipse(image, (int(width * 0.58), int(height * 0.43)), (10, 5), 0, 0, 360, (0.95, 0.95, 0.90), -1)
    cv2.circle(image, (int(width * 0.42), int(height * 0.43)), 3, (0.05, 0.04, 0.03), -1)
    cv2.circle(image, (int(width * 0.58), int(height * 0.43)), 3, (0.05, 0.04, 0.03), -1)
    cv2.ellipse(image, (center[0], int(height * 0.66)), (24, 9), 0, 0, 360, (0.42, 0.11, 0.12), -1)
    cv2.rectangle(image, (center[0] - 14, int(height * 0.64)), (center[0] + 14, int(height * 0.67)), (0.88, 0.82, 0.67), -1)
    rng = np.random.default_rng(4)
    noise = rng.normal(0, 0.025, image.shape).astype(np.float32)
    return np.clip(image + noise, 0, 1)


@pytest.fixture()
def demo_image_path() -> Path | None:
    path = Path(__file__).resolve().parents[2] / "demo" / "before.jpg"
    return path if path.exists() else None
