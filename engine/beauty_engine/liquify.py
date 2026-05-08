from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from . import landmark_indices as idx
from .debug import draw_handles, draw_warp_grid, write_heatmap, write_mask
from .face import FaceLandmarks
from .masks import RegionMasks
from .params import LiquifyParams
from .warp import jacobian_determinant, masked_blend, mls_similarity_maps, remap


@dataclass(frozen=True)
class HandleSet:
    source: np.ndarray
    target: np.ndarray
    active_mask: np.ndarray

    @property
    def has_motion(self) -> bool:
        return self.source.size > 0 and not np.allclose(self.source, self.target, atol=1e-4)


def apply_liquify(
    image: np.ndarray,
    face: FaceLandmarks | None,
    masks: RegionMasks | None,
    params: LiquifyParams,
    debug_dir: str | Path | None = None,
) -> np.ndarray:
    if face is None or masks is None or _is_zero(params):
        return image.copy()

    handles = build_face_handles(image.shape[:2], face, masks, params)
    if not handles.has_motion:
        return image.copy()

    map_x, map_y, det = _guarded_mls_maps(image.shape[:2], handles)
    warped = remap(image, map_x, map_y)
    blend_mask = np.clip(handles.active_mask, 0, 1)
    result = masked_blend(image, warped, blend_mask)

    if debug_dir:
        debug_path = Path(debug_dir)
        debug_path.mkdir(parents=True, exist_ok=True)
        draw_warp_grid(image, map_x, map_y, debug_path / "warp_grid.png")
        draw_handles(image, handles.source, handles.target, debug_path / "control_handles.png")
        write_mask(debug_path / "liquify_mask.png", blend_mask)
        write_heatmap(debug_path / "foldover_heatmap.png", det)
    return result


def build_face_handles(
    shape: tuple[int, int],
    face: FaceLandmarks,
    masks: RegionMasks,
    params: LiquifyParams,
) -> HandleSet:
    height, width = shape
    points = face.points_px(width, height)
    x, y, face_w, face_h = face.bbox
    center = np.array([x + face_w * 0.5, y + face_h * 0.54], dtype=np.float32)
    confidence_scale = float(np.clip((face.confidence - 0.40) / 0.55, 0.35, 1.0))

    sources: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    active_mask = np.zeros((height, width), dtype=np.float32)

    def add_fixed(items: np.ndarray) -> None:
        for point in _valid_points(items, width, height):
            sources.append(point)
            targets.append(point.copy())

    def add_move(items: np.ndarray, moved: np.ndarray) -> None:
        for point, target in zip(_valid_points(items, width, height), _valid_points(moved, width, height)):
            sources.append(point)
            targets.append(target)

    add_fixed(_image_border_anchors(width, height, count=9))
    add_fixed(_face_boundary_anchors(face, width, height, scale=1.20, count=44))

    dynamic_indices: set[int] = set()

    face_slim = float(params.face_slim) * confidence_scale
    if face_slim != 0:
        contour_indices = idx.LEFT_JAW[1:] + idx.RIGHT_JAW[1:] + idx.FACE_OVAL[8:29]
        contour = points[contour_indices, :2]
        moved = contour.copy()
        for row, point in enumerate(contour):
            side = np.sign(center[0] - point[0])
            vertical = np.clip((point[1] - (y + face_h * 0.34)) / max(face_h * 0.58, 1.0), 0, 1)
            side_weight = np.clip(abs(point[0] - center[0]) / max(face_w * 0.34, 1.0), 0.20, 1.0)
            moved[row, 0] += side * face_slim * face_w * 0.055 * side_weight
            moved[row, 1] -= face_slim * face_h * 0.006 * vertical
        add_move(contour, moved)
        dynamic_indices.update(contour_indices)
        active_mask = np.maximum(active_mask, masks.face * (1.0 - masks.protected * 0.88) * min(1.0, abs(face_slim) * 2.1))

    jawline = float(params.jawline) * confidence_scale
    if jawline != 0:
        jaw_indices = idx.LEFT_JAW[4:] + idx.RIGHT_JAW[4:] + idx.CHIN[:2]
        jaw = points[jaw_indices, :2]
        moved = jaw.copy()
        for row, point in enumerate(jaw):
            side = np.sign(center[0] - point[0])
            lower = np.clip((point[1] - (y + face_h * 0.56)) / max(face_h * 0.34, 1.0), 0.15, 1.0)
            moved[row, 0] += side * jawline * face_w * 0.040 * lower
            moved[row, 1] -= jawline * face_h * 0.018 * lower
        add_move(jaw, moved)
        dynamic_indices.update(jaw_indices)
        active_mask = np.maximum(active_mask, masks.face * (1.0 - masks.protected * 0.90) * min(1.0, abs(jawline) * 2.0))

    chin_length = float(params.chin_length) * confidence_scale
    if chin_length != 0:
        chin = points[idx.CHIN, :2]
        chin_center = np.mean(chin, axis=0, dtype=np.float32)
        moved = chin.copy()
        moved[:, 1] += chin_length * face_h * 0.055
        add_move(chin, moved)
        dynamic_indices.update(idx.CHIN)
        active_mask = np.maximum(
            active_mask,
            _radial_mask(shape, chin_center, face_w * 0.24, face_h * 0.22) * min(1.0, abs(chin_length) * 1.6),
        )

    eye_enlarge = max(0.0, float(params.eye_enlarge)) * confidence_scale
    if eye_enlarge > 0:
        for eye_indices in (idx.LEFT_EYE, idx.RIGHT_EYE):
            eye = points[eye_indices, :2]
            eye_center = np.mean(eye, axis=0, dtype=np.float32)
            delta = eye - eye_center
            moved = eye_center + delta * (1.0 + eye_enlarge * 0.32)
            add_move(eye, moved)
            dynamic_indices.update(eye_indices)
            radius = max(8.0, float(np.ptp(eye[:, 0])) * 1.65)
            active_mask = np.maximum(
                active_mask,
                _radial_mask(shape, eye_center, radius, radius * 0.82) * min(1.0, eye_enlarge * 1.8),
            )

    nose_slim = max(0.0, float(params.nose_slim)) * confidence_scale
    if nose_slim > 0:
        nose_indices = list(dict.fromkeys(idx.NOSE_LEFT + idx.NOSE_RIGHT + idx.NOSE_BRIDGE[-3:]))
        nose = points[nose_indices, :2]
        moved = nose.copy()
        nose_center_x = float(np.mean(points[idx.NOSE_BRIDGE, 0]))
        for row, point in enumerate(nose):
            side = np.sign(nose_center_x - point[0])
            moved[row, 0] += side * nose_slim * face_w * 0.026
        add_move(nose, moved)
        dynamic_indices.update(nose_indices)
        nose_center = np.mean(points[idx.NOSE_LEFT + idx.NOSE_RIGHT, :2], axis=0, dtype=np.float32)
        active_mask = np.maximum(
            active_mask,
            _radial_mask(shape, nose_center, face_w * 0.16, face_h * 0.19) * min(1.0, nose_slim * 1.7),
        )

    smile = max(0.0, float(params.smile)) * confidence_scale
    if smile > 0:
        mouth_indices = idx.LEFT_MOUTH_CORNER + idx.RIGHT_MOUTH_CORNER + idx.OUTER_LIPS[3:8]
        mouth = points[mouth_indices, :2]
        moved = mouth.copy()
        for row, point in enumerate(mouth):
            side = np.sign(point[0] - center[0])
            corner_weight = np.clip(abs(point[0] - center[0]) / max(face_w * 0.20, 1.0), 0.25, 1.0)
            moved[row, 0] += side * smile * face_w * 0.012 * corner_weight
            moved[row, 1] -= smile * face_h * 0.026 * corner_weight
        add_move(mouth, moved)
        dynamic_indices.update(mouth_indices)
        mouth_center = np.mean(points[idx.OUTER_LIPS, :2], axis=0, dtype=np.float32)
        active_mask = np.maximum(
            active_mask,
            _radial_mask(shape, mouth_center, face_w * 0.24, face_h * 0.15) * min(1.0, smile * 1.7),
        )

    protected_indices = [item for item in idx.ALL_PROTECTED + idx.NOSE_TIP if item not in dynamic_indices]
    add_fixed(points[protected_indices, :2])

    source = np.asarray(sources, dtype=np.float32)
    target = np.asarray(targets, dtype=np.float32)
    active_mask = np.clip(active_mask, 0, 1).astype(np.float32)
    return HandleSet(source=source, target=target, active_mask=active_mask)


def _guarded_mls_maps(shape: tuple[int, int], handles: HandleSet) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    source = handles.source
    displacement = handles.target - handles.source
    scale = 1.0
    best: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    for _attempt in range(5):
        target = source + displacement * scale
        map_x, map_y = mls_similarity_maps(shape, source, target)
        det = _foldover_probe(map_x, map_y)
        best = (map_x, map_y, det)
        if float(np.nanmin(det)) > 0.12:
            return best
        scale *= 0.62
    assert best is not None
    return best


def _foldover_probe(map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    height, width = map_x.shape
    probe_w = min(width, 256)
    probe_h = min(height, 256)
    small_x = cv2.resize(map_x.astype(np.float32), (probe_w, probe_h), interpolation=cv2.INTER_AREA)
    small_y = cv2.resize(map_y.astype(np.float32), (probe_w, probe_h), interpolation=cv2.INTER_AREA)
    return jacobian_determinant(small_x, small_y)


def _is_zero(params: LiquifyParams) -> bool:
    return (
        params.face_slim == 0
        and params.jawline == 0
        and params.chin_length == 0
        and params.eye_enlarge == 0
        and params.nose_slim == 0
        and params.smile == 0
    )


def _radial_mask(shape: tuple[int, int], center: np.ndarray, radius_x: float, radius_y: float) -> np.ndarray:
    height, width = shape
    yy, xx = np.mgrid[:height, :width].astype(np.float32)
    nx = (xx - float(center[0])) / max(radius_x, 1.0)
    ny = (yy - float(center[1])) / max(radius_y, 1.0)
    return np.exp(-(nx * nx + ny * ny)).astype(np.float32)


def _image_border_anchors(width: int, height: int, count: int) -> np.ndarray:
    xs = np.linspace(0, width - 1, count, dtype=np.float32)
    ys = np.linspace(0, height - 1, count, dtype=np.float32)
    top = np.column_stack([xs, np.zeros_like(xs)])
    bottom = np.column_stack([xs, np.full_like(xs, height - 1)])
    left = np.column_stack([np.zeros_like(ys), ys])
    right = np.column_stack([np.full_like(ys, width - 1), ys])
    return np.vstack([top, bottom, left, right])


def _face_boundary_anchors(
    face: FaceLandmarks, width: int, height: int, *, scale: float, count: int
) -> np.ndarray:
    x, y, face_w, face_h = face.bbox
    center_x = x + face_w * 0.5
    center_y = y + face_h * 0.54
    angles = np.linspace(0, np.pi * 2, count, endpoint=False, dtype=np.float32)
    points = np.column_stack(
        [
            center_x + np.cos(angles) * face_w * 0.56 * scale,
            center_y + np.sin(angles) * face_h * 0.58 * scale,
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
