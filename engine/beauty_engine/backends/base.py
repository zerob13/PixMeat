from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class DeviceInfo:
    type: str
    name: str
    available: bool


class ImageBackend(Protocol):
    name: str
    device: str

    def is_available(self) -> bool: ...

    def remap(self, image: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray: ...

    def gaussian_blur(self, image: np.ndarray, sigma: float) -> np.ndarray: ...

    def alpha_blend(self, base: np.ndarray, overlay: np.ndarray, mask: np.ndarray) -> np.ndarray: ...
