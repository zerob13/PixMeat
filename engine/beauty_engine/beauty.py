from __future__ import annotations

import cv2
import numpy as np

from .masks import RegionMasks
from .params import BeautyParams
from .warp import masked_blend


def apply_beauty(image: np.ndarray, masks: RegionMasks | None, params: BeautyParams) -> np.ndarray:
    result = image.copy()
    if masks is not None and params.eye_bright > 0:
        result = brighten_eyes(result, masks.eyes, params.eye_bright)
    if masks is not None and params.teeth_white > 0:
        result = whiten_teeth(result, masks.teeth, params.teeth_white)
    if params.brightness != 0:
        result = adjust_brightness(result, params.brightness)
    if params.soft_contrast != 0:
        result = adjust_soft_contrast(result, params.soft_contrast)
    return np.clip(result, 0, 1)


def adjust_brightness(image: np.ndarray, amount: float) -> np.ndarray:
    if amount >= 0:
        return np.clip(image + (1.0 - image) * amount * 0.35, 0, 1)
    return np.clip(image * (1.0 + amount * 0.35), 0, 1)


def adjust_soft_contrast(image: np.ndarray, amount: float) -> np.ndarray:
    factor = 1.0 + amount * 0.4
    return np.clip(0.5 + (image - 0.5) * factor, 0, 1)


def brighten_eyes(image: np.ndarray, eye_mask: np.ndarray, amount: float) -> np.ndarray:
    hsv = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    saturation = hsv[:, :, 1] / 255.0
    value = hsv[:, :, 2] / 255.0
    candidate = eye_mask * (saturation < 0.46) * (value > 0.28)
    lifted = image + (1.0 - image) * (0.18 * amount)
    contrast = np.clip(0.5 + (lifted - 0.5) * (1.0 + amount * 0.12), 0, 1)
    return masked_blend(image, contrast, np.clip(candidate * amount, 0, 1))


def whiten_teeth(image: np.ndarray, mouth_inner_mask: np.ndarray, amount: float) -> np.ndarray:
    hsv = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    saturation = hsv[:, :, 1] / 255.0
    value = hsv[:, :, 2] / 255.0
    candidate = mouth_inner_mask * (value > 0.28) * (saturation < 0.72)
    lab = cv2.cvtColor(np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab[:, :, 0] = np.clip(lab[:, :, 0] + amount * 16.0 * candidate, 0, 255)
    lab[:, :, 2] = lab[:, :, 2] * (1.0 - candidate * amount * 0.22) + 128.0 * (candidate * amount * 0.22)
    whitened = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
    return masked_blend(image, whitened, np.clip(candidate * amount, 0, 1))
