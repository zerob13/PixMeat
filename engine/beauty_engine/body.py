from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .debug import draw_handles, write_mask
from .face import FaceLandmarks
from .params import BodyParams
from .warp import masked_blend, mls_similarity_maps, remap


@dataclass(frozen=True)
class BodyHandles:
    source: np.ndarray
    target: np.ndarray
    mask: np.ndarray

    @property
    def has_motion(self) -> bool:
        return self.source.size > 0 and not np.allclose(self.source, self.target, atol=1e-4)


def apply_body_shape(
    image: np.ndarray,
    face: FaceLandmarks | None,
    params: BodyParams,
    *,
    debug_dir: str | Path | None = None,
) -> np.ndarray:
    if face is None or _is_zero(params):
        return image.copy()

    handles = build_body_handles(image.shape[:2], face, params)
    if not handles.has_motion:
        return image.copy()

    map_x, map_y = mls_similarity_maps(image.shape[:2], handles.source, handles.target, max_grid_points=12_000)
    warped = remap(image, map_x, map_y)
    result = masked_blend(image, warped, handles.mask)

    if debug_dir:
        debug_path = Path(debug_dir)
        debug_path.mkdir(parents=True, exist_ok=True)
        write_mask(debug_path / "body_shape_mask.png", handles.mask)
        draw_handles(image, handles.source, handles.target, debug_path / "body_control_handles.png")
    return result


def build_body_handles(shape: tuple[int, int], face: FaceLandmarks, params: BodyParams) -> BodyHandles:
    height, width = shape
    x, y, face_w, face_h = face.bbox
    face_center_x = x + face_w * 0.5
    body_center_x = float(np.clip(face_center_x + face_w * 0.18, width * 0.10, width * 0.90))
    top = float(np.clip(y + face_h * 0.68, 0, height - 1))
    bottom = float(np.clip(y + face_h * 4.35, top + face_h * 0.75, height - 1))
    body_h = bottom - top
    if body_h < max(30.0, face_h * 0.65):
        return BodyHandles(np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32), np.zeros(shape, dtype=np.float32))

    body_slim = float(np.clip(params.body_slim, 0, 1))
    waist_slim = float(np.clip(params.waist_slim, 0, 1))
    arm_slim = float(np.clip(params.arm_slim, 0, 1))

    sources: list[np.ndarray] = []
    targets: list[np.ndarray] = []

    def add_fixed(items: np.ndarray) -> None:
        for point in _valid_points(items, width, height):
            sources.append(point)
            targets.append(point.copy())

    def add_move(source: np.ndarray, target: np.ndarray) -> None:
        for point, moved in zip(_valid_points(source, width, height), _valid_points(target, width, height)):
            sources.append(point)
            targets.append(moved)

    add_fixed(_image_border_anchors(width, height, count=9))
    add_fixed(_face_guard_anchors(face, width, height, count=28))

    rows = np.linspace(0.0, 1.0, 7, dtype=np.float32)
    side_sources: list[np.ndarray] = []
    side_targets: list[np.ndarray] = []
    center_sources: list[np.ndarray] = []
    for t in rows:
        y_row = top + body_h * float(t)
        half_width = _body_half_width(face_w, t)
        waist_weight = float(np.exp(-((float(t) - 0.50) / 0.22) ** 2))
        shoulder_weight = float(np.exp(-((float(t) - 0.12) / 0.22) ** 2))
        arm_weight = max(0.18, shoulder_weight)
        inward = face_w * (
            body_slim * (0.08 + 0.10 * float(t))
            + waist_slim * 0.18 * waist_weight
            + arm_slim * 0.07 * arm_weight
        )
        left = np.array([body_center_x - half_width, y_row], dtype=np.float32)
        right = np.array([body_center_x + half_width, y_row], dtype=np.float32)
        side_sources.extend([left, right])
        side_targets.extend(
            [
                np.array([left[0] + inward, y_row], dtype=np.float32),
                np.array([right[0] - inward, y_row], dtype=np.float32),
            ]
        )
        center_sources.append(np.array([body_center_x, y_row], dtype=np.float32))

    add_move(np.asarray(side_sources, dtype=np.float32), np.asarray(side_targets, dtype=np.float32))
    add_fixed(np.asarray(center_sources, dtype=np.float32))

    if arm_slim > 0:
        arm_sources, arm_targets = _arm_handles(body_center_x, top, bottom, face_w, arm_slim)
        add_move(arm_sources, arm_targets)

    mask = body_shape_mask(shape, body_center_x, top, bottom, face_w, body_slim, waist_slim, arm_slim)
    return BodyHandles(
        np.asarray(sources, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        mask,
    )


def body_shape_mask(
    shape: tuple[int, int],
    center_x: float,
    top: float,
    bottom: float,
    face_w: float,
    body_slim: float,
    waist_slim: float,
    arm_slim: float,
) -> np.ndarray:
    height, width = shape
    yy, xx = np.mgrid[:height, :width].astype(np.float32)
    body_h = max(1.0, bottom - top)
    t = np.clip((yy - top) / body_h, 0, 1)
    half_width = _body_half_width(face_w, t)
    nx = np.abs(xx - float(center_x)) / np.maximum(half_width, 1.0)
    torso = np.exp(-(nx**4) * 1.65)
    vertical = _smoothstep(t) * _smoothstep(1.0 - t * 0.92)
    waist = np.exp(-((t - 0.50) / 0.24) ** 2) * np.exp(-(nx**2) * 0.80)
    side = np.exp(-((nx - 1.02) / 0.34) ** 2) * _smoothstep(t * 1.35) * _smoothstep(1.05 - t)
    strength = np.clip(body_slim * 0.60 * torso + waist_slim * 0.75 * waist + arm_slim * 0.50 * side, 0, 1)
    mask = np.clip(strength * vertical, 0, 1).astype(np.float32)
    mask[yy < top] = 0
    return cv2.GaussianBlur(mask, (0, 0), sigmaX=max(1.0, face_w * 0.025)).astype(np.float32)


def _arm_handles(center_x: float, top: float, bottom: float, face_w: float, amount: float) -> tuple[np.ndarray, np.ndarray]:
    rows = np.linspace(0.18, 0.92, 5, dtype=np.float32)
    sources: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    body_h = bottom - top
    for t in rows:
        y_row = top + body_h * float(t)
        half_width = _body_half_width(face_w, t) * (1.03 + 0.13 * float(t))
        inward = face_w * amount * (0.055 + 0.045 * float(t))
        left = np.array([center_x - half_width, y_row], dtype=np.float32)
        right = np.array([center_x + half_width, y_row], dtype=np.float32)
        sources.extend([left, right])
        targets.extend(
            [
                np.array([left[0] + inward, y_row], dtype=np.float32),
                np.array([right[0] - inward, y_row], dtype=np.float32),
            ]
        )
    return np.asarray(sources, dtype=np.float32), np.asarray(targets, dtype=np.float32)


def _body_half_width(face_w: float, t: float | np.ndarray) -> float | np.ndarray:
    t_arr = np.asarray(t, dtype=np.float32)
    shoulder = 1.35 - 0.18 * np.clip(t_arr, 0, 1)
    hip = 1.18 + 0.22 * np.clip(t_arr - 0.55, 0, 1)
    waist_dip = 0.18 * np.exp(-((t_arr - 0.50) / 0.22) ** 2)
    return face_w * np.maximum(0.86, shoulder * (1.0 - np.clip(t_arr - 0.35, 0, 1) * 0.25) + hip * 0.12 - waist_dip)


def _smoothstep(value: np.ndarray) -> np.ndarray:
    x = np.clip(value, 0, 1)
    return x * x * (3.0 - 2.0 * x)


def _image_border_anchors(width: int, height: int, count: int) -> np.ndarray:
    xs = np.linspace(0, width - 1, count, dtype=np.float32)
    ys = np.linspace(0, height - 1, count, dtype=np.float32)
    top = np.column_stack([xs, np.zeros_like(xs)])
    bottom = np.column_stack([xs, np.full_like(xs, height - 1)])
    left = np.column_stack([np.zeros_like(ys), ys])
    right = np.column_stack([np.full_like(ys, width - 1), ys])
    return np.vstack([top, bottom, left, right])


def _face_guard_anchors(face: FaceLandmarks, width: int, height: int, count: int) -> np.ndarray:
    x, y, face_w, face_h = face.bbox
    center_x = x + face_w * 0.5
    center_y = y + face_h * 0.52
    angles = np.linspace(0, np.pi * 2, count, endpoint=False, dtype=np.float32)
    points = np.column_stack(
        [
            center_x + np.cos(angles) * face_w * 0.72,
            center_y + np.sin(angles) * face_h * 0.70,
        ]
    ).astype(np.float32)
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    return points


def _valid_points(points: np.ndarray, width: int, height: int) -> np.ndarray:
    arr = np.asarray(points, dtype=np.float32).reshape(-1, 2).copy()
    finite = np.isfinite(arr).all(axis=1)
    arr = arr[finite]
    if arr.size == 0:
        return arr
    arr[:, 0] = np.clip(arr[:, 0], 0, width - 1)
    arr[:, 1] = np.clip(arr[:, 1], 0, height - 1)
    return arr


def _is_zero(params: BodyParams) -> bool:
    return params.body_slim == 0 and params.waist_slim == 0 and params.arm_slim == 0
