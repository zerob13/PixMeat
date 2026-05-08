from __future__ import annotations

import cv2
import numpy as np


class CpuBackend:
    name = "cpu"
    device = "cpu"

    def is_available(self) -> bool:
        return True

    def remap(self, image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
        return cv2.remap(
            image.astype(np.float32),
            map_x.astype(np.float32),
            map_y.astype(np.float32),
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )

    def gaussian_blur(self, image: np.ndarray, sigma: float) -> np.ndarray:
        kernel = max(3, int(round(sigma * 6)) | 1)
        return cv2.GaussianBlur(image.astype(np.float32), (kernel, kernel), sigmaX=sigma, sigmaY=sigma)

    def bilateral_like_filter(
        self, image: np.ndarray, radius: int, sigma_color: float, sigma_space: float
    ) -> np.ndarray:
        diameter = max(3, radius * 2 + 1)
        return cv2.bilateralFilter(
            image.astype(np.float32),
            diameter,
            sigmaColor=sigma_color,
            sigmaSpace=sigma_space,
        )

    def alpha_blend(self, base: np.ndarray, overlay: np.ndarray, mask: np.ndarray) -> np.ndarray:
        alpha = mask[..., None].astype(np.float32)
        return np.clip(base * (1.0 - alpha) + overlay * alpha, 0.0, 1.0)
