from __future__ import annotations

from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from .beauty import apply_beauty
from .body import apply_body_shape
from .debug import write_mask
from .face import FaceLandmarks, find_face
from .liquify import apply_liquify
from .masks import RegionMasks, build_masks
from .params import EditParams
from .smoothing import apply_skin
from .types import AnalysisResult

ProgressCallback = Callable[[float, str], None]


def process_image(
    image: np.ndarray,
    faces: list[FaceLandmarks],
    active_face_id: str | None,
    params: EditParams,
    *,
    analysis_result: AnalysisResult | None = None,
    debug_dir: str | Path | None = None,
    progress: ProgressCallback | None = None,
) -> np.ndarray:
    progress = progress or (lambda _value, _stage: None)
    progress(0.05, "select_face")
    active_face = find_face(faces, active_face_id)

    masks: RegionMasks | None = None
    if active_face is not None:
        masks = build_masks(image.shape[:2], active_face)
        masks = _with_analysis_skin_mask(masks, analysis_result, image.shape[:2])
        if debug_dir:
            debug_path = Path(debug_dir)
            debug_path.mkdir(parents=True, exist_ok=True)
            write_mask(debug_path / "face_mask.png", masks.face)
            write_mask(debug_path / "skin_mask.png", masks.skin)
            write_mask(debug_path / "eye_mask.png", masks.eyes)
            write_mask(debug_path / "mouth_mask.png", masks.mouth)
    elif analysis_result is not None:
        masks = _analysis_only_masks(analysis_result, image.shape[:2])

    progress(0.16, "body_shape")
    result = apply_body_shape(image, active_face, params.body, analysis_result=analysis_result, debug_dir=debug_dir)

    progress(0.28, "liquify")
    result = apply_liquify(result, active_face, masks, params.liquify, debug_dir=debug_dir)

    progress(0.55, "skin")
    result = apply_skin(result, masks, params.skin, skin_mask_override=_analysis_skin_mask(analysis_result, image.shape[:2]), debug_dir=str(debug_dir) if debug_dir else None)

    progress(0.78, "beauty")
    result = apply_beauty(result, masks, params.beauty)

    progress(1.0, "done")
    return np.clip(result, 0, 1).astype(np.float32)


def _with_analysis_skin_mask(masks: RegionMasks, analysis_result: AnalysisResult | None, shape: tuple[int, int]) -> RegionMasks:
    skin_mask = _analysis_skin_mask(analysis_result, shape)
    if skin_mask is None:
        return masks
    protected = np.clip(np.maximum(masks.protected, _analysis_exclusion_mask(analysis_result, shape)), 0, 1)
    return RegionMasks(
        face=masks.face,
        skin=np.clip(skin_mask, 0, 1).astype(np.float32),
        eyes=masks.eyes,
        mouth=masks.mouth,
        teeth=masks.teeth,
        protected=protected,
    )


def _analysis_only_masks(analysis_result: AnalysisResult, shape: tuple[int, int]) -> RegionMasks | None:
    skin_mask = _analysis_skin_mask(analysis_result, shape)
    if skin_mask is None:
        return None
    zeros = np.zeros(shape, dtype=np.float32)
    face = _analysis_region_mask(analysis_result, "face_region", shape)
    left_eye = _analysis_region_mask(analysis_result, "left_eye_region", shape)
    right_eye = _analysis_region_mask(analysis_result, "right_eye_region", shape)
    mouth = _analysis_region_mask(analysis_result, "mouth_region", shape)
    return RegionMasks(
        face=face if face is not None else zeros,
        skin=skin_mask,
        eyes=np.maximum(left_eye if left_eye is not None else zeros, right_eye if right_eye is not None else zeros),
        mouth=mouth if mouth is not None else zeros,
        teeth=zeros,
        protected=_analysis_exclusion_mask(analysis_result, shape),
    )


def _analysis_skin_mask(analysis_result: AnalysisResult | None, shape: tuple[int, int]) -> np.ndarray | None:
    if analysis_result is None:
        return None
    mask = analysis_result.masks.get("skin_final_mask")
    return _fit_mask(mask, shape)


def _analysis_exclusion_mask(analysis_result: AnalysisResult | None, shape: tuple[int, int]) -> np.ndarray:
    if analysis_result is None:
        return np.zeros(shape, dtype=np.float32)
    fitted = _fit_mask(analysis_result.masks.get("skin_exclusion_mask"), shape)
    return fitted if fitted is not None else np.zeros(shape, dtype=np.float32)


def _analysis_region_mask(analysis_result: AnalysisResult, name: str, shape: tuple[int, int]) -> np.ndarray | None:
    region = analysis_result.regions.get(name)
    if region is None:
        return None
    return _fit_mask(region.mask, shape)


def _fit_mask(mask: np.ndarray | None, shape: tuple[int, int]) -> np.ndarray | None:
    if mask is None:
        return None
    arr = np.clip(mask.astype(np.float32), 0, 1)
    if arr.shape[:2] == shape:
        return arr
    resized = cv2.resize(arr, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
    return np.clip(resized, 0, 1).astype(np.float32)
