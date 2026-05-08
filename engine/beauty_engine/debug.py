from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .face import FaceLandmarks
from .io import to_uint8, write_image


def draw_landmarks(image: np.ndarray, face: FaceLandmarks, output_path: str | Path) -> None:
    height, width = image.shape[:2]
    canvas = to_uint8(image).copy()
    points = face.points_px(width, height)
    for point in points:
        x, y = int(round(point[0])), int(round(point[1]))
        if 0 <= x < width and 0 <= y < height:
            cv2.circle(canvas, (x, y), 1, (0, 220, 255), -1)
    x, y, w, h = [int(round(v)) for v in face.bbox]
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (255, 180, 0), 2)
    write_image(output_path, canvas.astype(np.float32) / 255.0)


def write_mask(path: str | Path, mask: np.ndarray) -> None:
    rgb = np.dstack([mask, mask, mask]).astype(np.float32)
    write_image(path, rgb)


def draw_warp_grid(
    image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray, output_path: str | Path, spacing: int = 48
) -> None:
    canvas = to_uint8(image).copy()
    height, width = image.shape[:2]
    for y in range(0, height, spacing):
        points = np.array([[map_x[y, x], map_y[y, x]] for x in range(0, width, spacing)], dtype=np.int32)
        cv2.polylines(canvas, [points], False, (0, 220, 255), 1)
    for x in range(0, width, spacing):
        points = np.array([[map_x[y, x], map_y[y, x]] for y in range(0, height, spacing)], dtype=np.int32)
        cv2.polylines(canvas, [points], False, (0, 220, 255), 1)
    write_image(output_path, canvas.astype(np.float32) / 255.0)
