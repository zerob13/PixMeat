from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import EngineError


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


@dataclass(frozen=True)
class ImageData:
    rgb: np.ndarray
    alpha: np.ndarray | None
    width: int
    height: int
    mode: str
    exif: bytes | None = None


def read_image(path: str | Path) -> ImageData:
    image_path = Path(path)
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise EngineError("unsupported_format", f"Unsupported image format: {image_path.suffix}")

    try:
        with Image.open(image_path) as source:
            source = ImageOps.exif_transpose(source)
            exif = source.info.get("exif")
            mode = source.mode
            rgba = source.convert("RGBA") if "A" in source.getbands() else source.convert("RGB")
            arr = np.asarray(rgba)
    except (FileNotFoundError, PermissionError, UnidentifiedImageError, OSError) as exc:
        raise EngineError("read_error", f"Cannot open image: {image_path.name}", {"cause": str(exc)}) from exc

    if arr.ndim != 3:
        raise EngineError("read_error", "Decoded image has invalid shape")

    if arr.shape[2] == 4:
        rgb_u8 = arr[:, :, :3]
        alpha = arr[:, :, 3].astype(np.float32) / 255.0
    else:
        rgb_u8 = arr[:, :, :3]
        alpha = None

    rgb = rgb_u8.astype(np.float32) / 255.0
    height, width = rgb.shape[:2]
    return ImageData(rgb=rgb, alpha=alpha, width=width, height=height, mode=mode, exif=exif)


def to_uint8(rgb: np.ndarray) -> np.ndarray:
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


def write_image(
    path: str | Path,
    rgb: np.ndarray,
    *,
    alpha: np.ndarray | None = None,
    quality: int = 92,
    keep_metadata: bool = True,
    exif: bytes | None = None,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    rgb_u8 = to_uint8(rgb)

    if alpha is not None and suffix in {".png", ".tif", ".tiff"}:
        alpha_u8 = np.clip(alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)
        image = Image.fromarray(np.dstack([rgb_u8, alpha_u8]), "RGBA")
    else:
        image = Image.fromarray(rgb_u8, "RGB")

    try:
        save_kwargs: dict[str, Any] = {}
        if suffix in {".jpg", ".jpeg"}:
            save_kwargs.update({"quality": int(np.clip(quality, 1, 100)), "subsampling": 0, "optimize": True})
            if keep_metadata and exif:
                save_kwargs["exif"] = exif
            image.save(output_path, "JPEG", **save_kwargs)
        elif suffix == ".png":
            image.save(output_path, "PNG")
        elif suffix in {".tif", ".tiff"}:
            image.save(output_path, "TIFF")
        else:
            raise EngineError("unsupported_format", f"Unsupported output format: {suffix}")
    except OSError as exc:
        raise EngineError("write_error", f"Cannot write image: {output_path.name}", {"cause": str(exc)}) from exc


def resize_max_side(image: np.ndarray, max_side: int) -> np.ndarray:
    height, width = image.shape[:2]
    max_current = max(height, width)
    if max_current <= max_side:
        return image.copy()
    scale = max_side / max_current
    new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    pil = Image.fromarray(to_uint8(image), "RGB")
    return np.asarray(pil.resize(new_size, Image.Resampling.LANCZOS)).astype(np.float32) / 255.0


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    import json

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf8")
