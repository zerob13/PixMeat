from __future__ import annotations

import cv2
import numpy as np


def identity_maps(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    height, width = shape
    x, y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    return x, y


def remap(image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    return cv2.remap(
        image.astype(np.float32),
        map_x.astype(np.float32),
        map_y.astype(np.float32),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def masked_blend(base: np.ndarray, overlay: np.ndarray, mask: np.ndarray) -> np.ndarray:
    alpha = np.clip(mask, 0, 1)[..., None].astype(np.float32)
    return np.clip(base * (1.0 - alpha) + overlay * alpha, 0.0, 1.0)


def apply_translation(image: np.ndarray, dx: float, dy: float) -> np.ndarray:
    height, width = image.shape[:2]
    map_x, map_y = identity_maps((height, width))
    return remap(image, map_x - dx, map_y - dy)
