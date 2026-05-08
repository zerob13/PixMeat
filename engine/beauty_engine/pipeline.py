from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

from .beauty import apply_beauty
from .debug import write_mask
from .face import FaceLandmarks, find_face
from .liquify import apply_liquify
from .masks import RegionMasks, build_masks
from .params import EditParams
from .smoothing import apply_skin

ProgressCallback = Callable[[float, str], None]


def process_image(
    image: np.ndarray,
    faces: list[FaceLandmarks],
    active_face_id: str | None,
    params: EditParams,
    *,
    debug_dir: str | Path | None = None,
    progress: ProgressCallback | None = None,
) -> np.ndarray:
    progress = progress or (lambda _value, _stage: None)
    progress(0.05, "select_face")
    active_face = find_face(faces, active_face_id)

    masks: RegionMasks | None = None
    if active_face is not None:
        masks = build_masks(image.shape[:2], active_face)
        if debug_dir:
            debug_path = Path(debug_dir)
            debug_path.mkdir(parents=True, exist_ok=True)
            write_mask(debug_path / "face_mask.png", masks.face)
            write_mask(debug_path / "skin_mask.png", masks.skin)
            write_mask(debug_path / "eye_mask.png", masks.eyes)
            write_mask(debug_path / "mouth_mask.png", masks.mouth)

    progress(0.20, "liquify")
    result = apply_liquify(image, active_face, masks, params.liquify, debug_dir=debug_dir)

    progress(0.55, "skin")
    result = apply_skin(result, masks, params.skin, debug_dir=str(debug_dir) if debug_dir else None)

    progress(0.78, "beauty")
    result = apply_beauty(result, masks, params.beauty)

    progress(1.0, "done")
    return np.clip(result, 0, 1).astype(np.float32)
