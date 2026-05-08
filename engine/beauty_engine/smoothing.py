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
    amount = float(np.clip(smooth, 0, 1))
    texture = float(np.clip(texture_keep, 0, 1))
    if amount <= 0 or not np.any(skin_mask > 0.01):
        return image.copy()

    base = edge_preserving_base(image, amount)
    detail = image.astype(np.float32) - base
    detail_keep = 0.18 + texture * 0.82
    reconstructed = np.clip(base + detail * detail_keep, 0, 1)
    blend_mask = skin_blend_mask(image, skin_mask, amount)
    return masked_blend(image, reconstructed, blend_mask)


def edge_preserving_base(image: np.ndarray, amount: float) -> np.ndarray:
    image_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    sigma_s = 14.0 + amount * 38.0
    sigma_r = 0.08 + amount * 0.16
    try:
        base_u8 = cv2.edgePreservingFilter(image_u8, flags=cv2.RECURS_FILTER, sigma_s=sigma_s, sigma_r=sigma_r)
    except cv2.error:
        diameter = 5 if amount < 0.5 else 9
        base_u8 = cv2.bilateralFilter(
            image_u8,
            diameter,
            sigmaColor=18.0 + amount * 42.0,
            sigmaSpace=6.0 + amount * 12.0,
        )
    return base_u8.astype(np.float32) / 255.0


def skin_blend_mask(image: np.ndarray, skin_mask: np.ndarray, amount: float) -> np.ndarray:
    strong_edges = strong_edge_mask(image, skin_mask)
    protected = np.clip(1.0 - strong_edges * 0.82, 0, 1)
    mask = np.clip(skin_mask * protected, 0, 1).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=1.2 + amount * 1.4)
    return np.clip(mask * min(0.88, amount * 0.92), 0, 1).astype(np.float32)


def strong_edge_mask(image: np.ndarray, skin_mask: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray /= 255.0
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    skin_values = magnitude[skin_mask > 0.12]
    threshold = float(np.quantile(skin_values, 0.86)) if skin_values.size else 0.08
    threshold = max(0.045, threshold)
    edge = np.clip((magnitude - threshold) / max(threshold * 1.8, 0.001), 0, 1)
    edge = cv2.dilate(edge, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    return cv2.GaussianBlur(edge.astype(np.float32), (0, 0), sigmaX=1.0)


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
