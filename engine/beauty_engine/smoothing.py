from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .debug import write_mask
from .masks import RegionMasks
from .params import SkinParams
from .warp import masked_blend


def apply_skin(
    image: np.ndarray,
    masks: RegionMasks | None,
    params: SkinParams,
    *,
    debug_dir: str | Path | None = None,
) -> np.ndarray:
    if masks is None:
        return image.copy()
    skin_mask = refined_skin_mask(image, masks)
    if debug_dir:
        output_dir = Path(debug_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_mask(output_dir / "refined_skin_mask.png", skin_mask)
    result = image.copy()
    if params.skin_smooth > 0:
        result = smooth_skin(result, skin_mask, params.skin_smooth, params.texture_keep)
    if params.blemish_soften > 0:
        result = soften_blemishes(result, skin_mask, params.blemish_soften)
    if params.skin_tone_even > 0:
        result = even_skin_tone(result, skin_mask, params.skin_tone_even)
    return np.clip(result, 0, 1)


def smooth_skin(image: np.ndarray, skin_mask: np.ndarray, smooth: float, texture_keep: float) -> np.ndarray:
    amount = float(np.clip(smooth, 0, 1))
    texture = float(np.clip(texture_keep, 0, 1))
    if amount <= 0 or not np.any(skin_mask > 0.01):
        return image.copy()

    base = guided_base(image, radius=int(7 + amount * 22), eps=0.004 + amount * 0.012)
    smooth_base = guided_base(base, radius=int(10 + amount * 34), eps=0.010 + amount * 0.018)
    detail = image.astype(np.float32) - base
    detail_keep = 0.18 + texture * 0.68
    pore_floor = np.clip(np.abs(detail) * (0.16 + texture * 0.16), 0, 0.035)
    restored_detail = detail * detail_keep + np.sign(detail) * pore_floor * (1.0 - detail_keep)
    reconstructed = np.clip(smooth_base + restored_detail, 0, 1)
    blend_mask = skin_blend_mask(image, skin_mask, amount)
    return masked_blend(image, reconstructed, blend_mask)


def refined_skin_mask(image: np.ndarray, masks: RegionMasks) -> np.ndarray:
    face_skin = np.clip(masks.skin, 0, 1).astype(np.float32)
    color_mask = _skin_chroma_mask(image, face_skin)
    combined = np.maximum(face_skin, color_mask * 0.82)
    combined = np.clip(combined - masks.protected * 0.96, 0, 1)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    luma = _luma(image)
    refined = guided_filter(luma, combined, radius=18, eps=1e-3)
    return np.clip(refined, 0, 1).astype(np.float32)


def guided_base(image: np.ndarray, radius: int, eps: float) -> np.ndarray:
    guide = _luma(image)
    channels = [guided_filter(guide, image[:, :, channel], radius=radius, eps=eps) for channel in range(3)]
    return np.clip(np.stack(channels, axis=2), 0, 1).astype(np.float32)


def guided_filter(guide: np.ndarray, src: np.ndarray, radius: int, eps: float) -> np.ndarray:
    guide_f = guide.astype(np.float32)
    src_f = src.astype(np.float32)
    size = (radius * 2 + 1, radius * 2 + 1)
    mean_i = cv2.boxFilter(guide_f, cv2.CV_32F, size, normalize=True, borderType=cv2.BORDER_REFLECT_101)
    mean_p = cv2.boxFilter(src_f, cv2.CV_32F, size, normalize=True, borderType=cv2.BORDER_REFLECT_101)
    corr_i = cv2.boxFilter(guide_f * guide_f, cv2.CV_32F, size, normalize=True, borderType=cv2.BORDER_REFLECT_101)
    corr_ip = cv2.boxFilter(guide_f * src_f, cv2.CV_32F, size, normalize=True, borderType=cv2.BORDER_REFLECT_101)
    var_i = corr_i - mean_i * mean_i
    cov_ip = corr_ip - mean_i * mean_p
    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i
    mean_a = cv2.boxFilter(a, cv2.CV_32F, size, normalize=True, borderType=cv2.BORDER_REFLECT_101)
    mean_b = cv2.boxFilter(b, cv2.CV_32F, size, normalize=True, borderType=cv2.BORDER_REFLECT_101)
    return np.clip(mean_a * guide_f + mean_b, 0, 1).astype(np.float32)


def skin_blend_mask(image: np.ndarray, skin_mask: np.ndarray, amount: float) -> np.ndarray:
    strong_edges = strong_edge_mask(image, skin_mask)
    protected = np.clip(1.0 - strong_edges * 0.95, 0, 1)
    mask = np.clip(skin_mask * protected, 0, 1).astype(np.float32)
    mask = guided_filter(_luma(image), mask, radius=int(6 + amount * 14), eps=1e-3)
    mask = np.clip(mask * protected, 0, 1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=1.0 + amount * 1.6)
    mask = np.clip(mask * protected, 0, 1)
    return np.clip(mask * min(0.86, 0.12 + amount * 0.82), 0, 1).astype(np.float32)


def strong_edge_mask(image: np.ndarray, skin_mask: np.ndarray) -> np.ndarray:
    gray = _luma(image)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    skin_values = magnitude[skin_mask > 0.12]
    threshold = float(np.quantile(skin_values, 0.80)) if skin_values.size else 0.08
    threshold = max(0.045, threshold)
    edge = np.clip((magnitude - threshold) / max(threshold * 1.8, 0.001), 0, 1)
    edge = cv2.dilate(edge, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return cv2.GaussianBlur(edge.astype(np.float32), (0, 0), sigmaX=1.2)


def even_skin_tone(image: np.ndarray, skin_mask: np.ndarray, amount: float) -> np.ndarray:
    amount = float(np.clip(amount, 0, 1))
    lab = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    smooth_l = guided_filter(lab[:, :, 0] / 255.0, lab[:, :, 0] / 255.0, radius=int(18 + amount * 28), eps=0.012)
    blur = cv2.GaussianBlur(lab, (0, 0), sigmaX=10.0 + amount * 16.0)
    tone = lab.copy()
    tone[:, :, 0] = lab[:, :, 0] * (1.0 - amount * 0.18) + smooth_l * 255.0 * (amount * 0.18)
    tone[:, :, 0] = np.clip(tone[:, :, 0] + amount * 16.0, 0, 255)
    tone[:, :, 1] = lab[:, :, 1] * (1.0 - amount * 0.58) + blur[:, :, 1] * (amount * 0.58)
    tone[:, :, 2] = lab[:, :, 2] * (1.0 - amount * 0.50) + blur[:, :, 2] * (amount * 0.50)
    rgb = cv2.cvtColor(np.clip(tone, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
    blend = guided_filter(_luma(image), skin_mask, radius=14, eps=1e-3)
    return masked_blend(image, rgb, np.clip(blend * amount * 0.82, 0, 1))


def soften_blemishes(image: np.ndarray, skin_mask: np.ndarray, amount: float) -> np.ndarray:
    amount = float(np.clip(amount, 0, 1))
    image_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    median = cv2.medianBlur(image_u8, 7).astype(np.float32) / 255.0
    lab = cv2.cvtColor(image_u8, cv2.COLOR_RGB2LAB).astype(np.float32)
    local_l = cv2.GaussianBlur(lab[:, :, 0], (0, 0), sigmaX=3.0)
    red_spot = np.clip((lab[:, :, 1] - cv2.GaussianBlur(lab[:, :, 1], (0, 0), sigmaX=5.0) - 3.5) / 13.0, 0, 1)
    dark_spot = np.clip((local_l - lab[:, :, 0] - 4.0) / 18.0, 0, 1)
    texture_diff = np.mean(np.abs(image - median), axis=2)
    if np.any(skin_mask > 0.2):
        threshold = float(np.quantile(texture_diff[skin_mask > 0.2], 0.74))
    else:
        threshold = 1.0
    contrast_spot = np.clip((texture_diff - threshold) / max(threshold * 1.8, 0.001), 0, 1)
    spot = np.maximum.reduce([red_spot, dark_spot, contrast_spot]) * (skin_mask > 0.18)
    spot = cv2.morphologyEx(spot.astype(np.float32), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    spot = cv2.GaussianBlur(spot, (0, 0), sigmaX=1.25)
    return masked_blend(image, median, np.clip(spot * amount * 0.72, 0, 1))


def _skin_chroma_mask(image: np.ndarray, face_skin: np.ndarray) -> np.ndarray:
    image_u8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(image_u8, cv2.COLOR_RGB2LAB).astype(np.float32)
    hsv = cv2.cvtColor(image_u8, cv2.COLOR_RGB2HSV)
    ycrcb = cv2.cvtColor(image_u8, cv2.COLOR_RGB2YCrCb)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    generic = (cr > 126) & (cr < 182) & (cb > 70) & (cb < 146) & (sat > 24) & (sat < 175) & (val > 42) & (val < 232)

    samples = lab[face_skin > 0.35]
    if samples.shape[0] >= 32:
        center = np.median(samples[:, 1:3], axis=0)
        spread = np.percentile(np.abs(samples[:, 1:3] - center), 75, axis=0) + 4.0
        distance = np.sqrt(np.sum(((lab[:, :, 1:3] - center) / spread) ** 2, axis=2))
        learned = distance < 2.10
        mask = generic & learned
    else:
        mask = generic

    mask_f = mask.astype(np.float32)
    mask_f = cv2.morphologyEx(mask_f, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask_f = cv2.morphologyEx(mask_f, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask_f = _filter_skin_components(mask_f, face_skin)
    return cv2.GaussianBlur(mask_f, (0, 0), sigmaX=2.0).astype(np.float32)


def _luma(image: np.ndarray) -> np.ndarray:
    return np.clip(image[:, :, 0] * 0.299 + image[:, :, 1] * 0.587 + image[:, :, 2] * 0.114, 0, 1).astype(np.float32)


def _filter_skin_components(mask: np.ndarray, face_skin: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    face_pixels = np.argwhere(face_skin > 0.25)
    if face_pixels.size == 0:
        return mask

    y_min, x_min = np.min(face_pixels, axis=0)
    y_max, x_max = np.max(face_pixels, axis=0)
    face_w = max(8, int(x_max - x_min + 1))
    face_h = max(8, int(y_max - y_min + 1))
    face_cx = (x_min + x_max) * 0.5
    roi_left = max(0, int(face_cx - face_w * 4.6))
    roi_right = min(width, int(face_cx + face_w * 4.6))
    roi_top = max(0, int(y_max - face_h * 0.15))

    binary = (mask > 0.18).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
    filtered = np.zeros_like(mask, dtype=np.float32)
    image_area = float(height * width)

    for label in range(1, count):
        x, y, comp_w, comp_h, area = [int(value) for value in stats[label]]
        if area <= 0:
            continue
        x2 = x + comp_w
        y2 = y + comp_h
        component = labels[y:y2, x:x2] == label
        face_overlap = np.any(face_skin[y:y2, x:x2][component] > 0.12)
        in_body_roi = x2 > roi_left and x < roi_right and y >= roi_top
        area_ratio = area / image_area
        fill = area / max(1, comp_w * comp_h)
        too_large = area_ratio > 0.045 or (comp_w > width * 0.42 and comp_h > height * 0.10)
        too_small = area_ratio < 0.000015 and not face_overlap
        too_sparse = fill < 0.08 and not face_overlap
        if face_overlap and not too_large:
            filtered[y:y2, x:x2][component] = 1.0
        elif in_body_roi and not too_large and not too_small and not too_sparse:
            filtered[y:y2, x:x2][component] = 1.0

    return filtered
