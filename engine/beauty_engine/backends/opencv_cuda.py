from __future__ import annotations


def is_opencv_cuda_available() -> bool:
    try:
        import cv2

        return bool(hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0)
    except Exception:
        return False
