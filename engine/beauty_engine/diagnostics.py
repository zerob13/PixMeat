from __future__ import annotations

import platform
import sys

from . import __version__
from .backends.base import DeviceInfo
from .backends.opencv_cuda import is_opencv_cuda_available
from .backends.torch_backend import probe_torch


def get_health(preferred_backend: str = "auto") -> dict[str, object]:
    torch_probe = probe_torch()
    devices = [
        DeviceInfo(type="cpu", name="CPU", available=True),
        DeviceInfo(type="cuda", name=torch_probe.cuda_name or "CUDA", available=torch_probe.cuda),
        DeviceInfo(type="mps", name="Apple GPU", available=torch_probe.mps),
        DeviceInfo(type="opencv_cuda", name="OpenCV CUDA", available=is_opencv_cuda_available()),
    ]

    available = [device.type for device in devices if device.available]
    active = choose_backend(preferred_backend, available)
    return {
        "status": "ready",
        "version": __version__,
        "platform": sys.platform,
        "python_version": platform.python_version(),
        "available_backends": available,
        "active_backend": active,
        "devices": [device.__dict__ for device in devices],
    }


def choose_backend(preferred_backend: str, available: list[str]) -> str:
    if preferred_backend != "auto" and preferred_backend in available:
        return preferred_backend
    if sys.platform == "win32":
        for candidate in ("cuda", "opencv_cuda", "cpu"):
            if candidate in available:
                return candidate
    if sys.platform == "darwin":
        for candidate in ("mps", "cpu"):
            if candidate in available:
                return candidate
    return "cpu"
