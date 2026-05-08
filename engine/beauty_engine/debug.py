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


def write_heatmap(path: str | Path, values: np.ndarray) -> None:
    clipped = np.clip(values.astype(np.float32), 0, 3)
    normalized = np.clip((clipped - 0.15) / 1.35, 0, 1)
    heat_u8 = np.clip(normalized * 255.0 + 0.5, 0, 255).astype(np.uint8)
    color = cv2.applyColorMap(255 - heat_u8, cv2.COLORMAP_INFERNO)
    rgb = cv2.cvtColor(color, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
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


def draw_handles(
    image: np.ndarray,
    source: np.ndarray,
    target: np.ndarray,
    output_path: str | Path,
) -> None:
    canvas = to_uint8(image).copy()
    height, width = image.shape[:2]
    max_dim = max(width, height)
    radius = max(2, int(round(max_dim * 0.0012)))
    for src, dst in zip(source.astype(np.float32), target.astype(np.float32)):
        sx, sy = int(round(src[0])), int(round(src[1]))
        tx, ty = int(round(dst[0])), int(round(dst[1]))
        if not (0 <= sx < width and 0 <= sy < height):
            continue
        color = (80, 220, 255) if abs(tx - sx) + abs(ty - sy) > 0.25 else (120, 180, 120)
        cv2.circle(canvas, (sx, sy), radius, color, -1)
        if 0 <= tx < width and 0 <= ty < height and (abs(tx - sx) + abs(ty - sy) > 0.25):
            cv2.arrowedLine(canvas, (sx, sy), (tx, ty), (255, 95, 60), max(1, radius // 2), tipLength=0.25)
    write_image(output_path, canvas.astype(np.float32) / 255.0)
