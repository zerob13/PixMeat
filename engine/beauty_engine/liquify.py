from __future__ import annotations

from pathlib import Path

import numpy as np

from . import landmark_indices as idx
from .debug import draw_warp_grid
from .face import FaceLandmarks
from .masks import RegionMasks
from .params import LiquifyParams
from .warp import identity_maps, masked_blend, remap


def apply_liquify(
    image: np.ndarray,
    face: FaceLandmarks | None,
    masks: RegionMasks | None,
    params: LiquifyParams,
    debug_dir: str | Path | None = None,
) -> np.ndarray:
    if face is None or masks is None or _is_zero(params):
        return image.copy()

    height, width = image.shape[:2]
    base_x, base_y = identity_maps((height, width))
    map_x = base_x.copy()
    map_y = base_y.copy()
    points = face.points_px(width, height)
    x, y, face_w, face_h = face.bbox
    center_x = x + face_w * 0.5
    center_y = y + face_h * 0.52

    xx = base_x
    yy = base_y
    face_radius_x = max(1.0, face_w * 0.52)
    face_radius_y = max(1.0, face_h * 0.56)
    nx = (xx - center_x) / face_radius_x
    ny = (yy - center_y) / face_radius_y
    face_falloff = np.exp(-(nx * nx * 1.4 + ny * ny * 0.8)).astype(np.float32)
    confidence_scale = float(np.clip((face.confidence - 0.45) / 0.53, 0.45, 1.0))
    shape_alpha = np.zeros((height, width), dtype=np.float32)
    feature_alpha = np.zeros((height, width), dtype=np.float32)

    if params.face_slim > 0:
        strength = params.face_slim * confidence_scale
        pull = strength * face_w * 0.10
        radius_x = max(8.0, face_w * 0.24)
        radius_y = max(10.0, face_h * 0.30)
        left_cheek = _region_center(points, idx.LEFT_JAW[1:7], np.array([x + face_w * 0.24, y + face_h * 0.66]))
        right_cheek = _region_center(points, idx.RIGHT_JAW[1:7], np.array([x + face_w * 0.76, y + face_h * 0.66]))
        left_falloff = _pull_region(map_x, map_y, xx, yy, left_cheek, pull, 0.0, radius_x, radius_y)
        right_falloff = _pull_region(map_x, map_y, xx, yy, right_cheek, -pull, 0.0, radius_x, radius_y)
        shape_alpha = np.maximum(shape_alpha, np.maximum(left_falloff, right_falloff) * min(1.0, strength * 1.8))

    if params.jawline > 0:
        strength = params.jawline * confidence_scale
        pull = strength * face_w * 0.075
        lift = strength * face_h * 0.018
        radius_x = max(8.0, face_w * 0.20)
        radius_y = max(10.0, face_h * 0.24)
        left_jaw = _region_center(points, idx.LEFT_JAW[4:], np.array([x + face_w * 0.30, y + face_h * 0.82]))
        right_jaw = _region_center(points, idx.RIGHT_JAW[4:], np.array([x + face_w * 0.70, y + face_h * 0.82]))
        left_falloff = _pull_region(map_x, map_y, xx, yy, left_jaw, pull, -lift, radius_x, radius_y)
        right_falloff = _pull_region(map_x, map_y, xx, yy, right_jaw, -pull, -lift, radius_x, radius_y)
        shape_alpha = np.maximum(shape_alpha, np.maximum(left_falloff, right_falloff) * min(1.0, strength * 1.9))

    if params.chin_length != 0:
        chin_center = np.mean(points[idx.CHIN, :2], axis=0)
        chin_falloff = _radial_falloff(xx, yy, chin_center, face_w * 0.20, face_h * 0.18)
        map_y -= params.chin_length * face_h * 0.06 * chin_falloff
        shape_alpha = np.maximum(shape_alpha, chin_falloff * min(1.0, abs(params.chin_length) * 1.4))

    if params.eye_enlarge > 0:
        for region in (idx.LEFT_EYE, idx.RIGHT_EYE):
            eye_points = points[region, :2]
            eye_center = np.mean(eye_points, axis=0)
            eye_radius = max(8.0, (np.max(eye_points[:, 0]) - np.min(eye_points[:, 0])) * 1.7)
            map_x, map_y, eye_falloff = _enlarge_region(
                map_x, map_y, xx, yy, eye_center, eye_radius, params.eye_enlarge * 0.18
            )
            feature_alpha = np.maximum(feature_alpha, eye_falloff * min(1.0, params.eye_enlarge * 1.6))

    if params.nose_slim > 0:
        nose_points = points[idx.NOSE_LEFT + idx.NOSE_RIGHT, :2]
        nose_center = np.mean(nose_points, axis=0)
        nose_falloff = _radial_falloff(xx, yy, nose_center, face_w * 0.15, face_h * 0.18)
        side = np.sign(xx - nose_center[0])
        map_x += side * params.nose_slim * face_w * 0.025 * nose_falloff
        feature_alpha = np.maximum(feature_alpha, nose_falloff * min(1.0, params.nose_slim * 1.5))

    if params.smile > 0:
        for region, side_sign in ((idx.LEFT_MOUTH_CORNER, -1.0), (idx.RIGHT_MOUTH_CORNER, 1.0)):
            corner = np.mean(points[region, :2], axis=0)
            corner_falloff = _radial_falloff(xx, yy, corner, face_w * 0.16, face_h * 0.12)
            map_y += params.smile * face_h * 0.025 * corner_falloff
            map_x -= side_sign * params.smile * face_w * 0.01 * corner_falloff
            feature_alpha = np.maximum(feature_alpha, corner_falloff * min(1.0, params.smile * 1.5))

    warped = remap(image, map_x, map_y)
    protected_shape = np.clip(1.0 - masks.protected * 0.9, 0, 1)
    shape_alpha = shape_alpha * masks.face * protected_shape
    blend_mask = np.clip(np.maximum(shape_alpha, feature_alpha), 0, 1)
    result = masked_blend(image, warped, blend_mask)

    if debug_dir:
        Path(debug_dir).mkdir(parents=True, exist_ok=True)
        draw_warp_grid(image, map_x, map_y, Path(debug_dir) / "warp_grid.png")
    return result


def _is_zero(params: LiquifyParams) -> bool:
    return (
        params.face_slim == 0
        and params.jawline == 0
        and params.chin_length == 0
        and params.eye_enlarge == 0
        and params.nose_slim == 0
        and params.smile == 0
    )


def _radial_falloff(
    xx: np.ndarray, yy: np.ndarray, center: np.ndarray, radius_x: float, radius_y: float
) -> np.ndarray:
    nx = (xx - center[0]) / max(radius_x, 1.0)
    ny = (yy - center[1]) / max(radius_y, 1.0)
    return np.exp(-(nx * nx + ny * ny)).astype(np.float32)


def _region_center(points: np.ndarray, indices: list[int], fallback: np.ndarray) -> np.ndarray:
    region = points[indices, :2]
    if region.size == 0 or not np.all(np.isfinite(region)):
        return fallback.astype(np.float32)
    return np.mean(region, axis=0).astype(np.float32)


def _pull_region(
    map_x: np.ndarray,
    map_y: np.ndarray,
    xx: np.ndarray,
    yy: np.ndarray,
    center: np.ndarray,
    delta_x: float,
    delta_y: float,
    radius_x: float,
    radius_y: float,
) -> np.ndarray:
    falloff = _radial_falloff(xx, yy, center, radius_x, radius_y)
    map_x -= delta_x * falloff
    map_y -= delta_y * falloff
    return falloff


def _enlarge_region(
    map_x: np.ndarray,
    map_y: np.ndarray,
    xx: np.ndarray,
    yy: np.ndarray,
    center: np.ndarray,
    radius: float,
    amount: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dx = xx - center[0]
    dy = yy - center[1]
    distance = np.sqrt(dx * dx + dy * dy)
    falloff = np.exp(-((distance / max(radius, 1.0)) ** 2)).astype(np.float32)
    scale = amount * falloff
    return map_x - dx * scale, map_y - dy * scale, falloff
