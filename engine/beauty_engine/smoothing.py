from __future__ import annotations

import cv2
import numpy as np

from .masks import RegionMasks
from .params import SkinParams
from .warp import masked_blend


def apply_skin(image: np.ndarray, masks: RegionMasks | None, params: SkinParams) -> np.ndarray:
    if masks is None:
        return image.copy()
    result = image.copy()
    if params.skin_smooth > 0:
        result = smooth_skin(result, masks.skin, params.skin_smooth, params.texture_keep)
    if params.skin_tone_even > 0:
        result = even_skin_tone(result, masks.skin, params.skin_tone_even)
    if params.blemish_soften > 0:
        result = soften_blemishes(result, masks.skin, params.blemish_soften)
    return np.clip(result, 0, 1)


def smooth_skin(image: np.ndarray, skin_mask: np.ndarray, smooth: float, texture_keep: float) -> np.ndarray:
    if smooth <= 0:
        return image.copy()
    low = cv2.bilateralFilter(image.astype(np.float32), 9, sigmaColor=0.08 + smooth * 0.12, sigmaSpace=9)
    high = image - cv2.GaussianBlur(image.astype(np.float32), (0, 0), sigmaX=1.2 + smooth * 2.0)
    smooth_low = cv2.GaussianBlur(low, (0, 0), sigmaX=2.0 + smooth * 4.0)
    reconstructed = np.clip(smooth_low + high * texture_keep, 0, 1)
    return masked_blend(image, reconstructed, skin_mask * smooth)


def even_skin_tone(image: np.ndarray, skin_mask: np.ndarray, amount: float) -> np.ndarray:
    lab = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    blur = cv2.GaussianBlur(lab, (0, 0), sigmaX=8.0 + amount * 12.0)
    lab[:, :, 1] = lab[:, :, 1] * (1.0 - skin_mask * amount) + blur[:, :, 1] * (skin_mask * amount)
    lab[:, :, 2] = lab[:, :, 2] * (1.0 - skin_mask * amount) + blur[:, :, 2] * (skin_mask * amount)
    rgb = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
    return masked_blend(image, rgb, skin_mask * amount)


def soften_blemishes(image: np.ndarray, skin_mask: np.ndarray, amount: float) -> np.ndarray:
    blur = cv2.medianBlur(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), 7).astype(np.float32) / 255.0
    diff = np.mean(np.abs(image - blur), axis=2)
    threshold = np.quantile(diff[skin_mask > 0.2], 0.72) if np.any(skin_mask > 0.2) else 1.0
    spot = ((diff > threshold) & (skin_mask > 0.2)).astype(np.float32)
    spot = cv2.morphologyEx(spot, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    spot = cv2.GaussianBlur(spot, (0, 0), sigmaX=1.2)
    return masked_blend(image, blur, np.clip(spot * amount, 0, 1))
