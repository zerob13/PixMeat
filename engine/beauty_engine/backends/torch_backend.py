from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TorchProbe:
    cuda: bool
    mps: bool
    cuda_name: str | None = None


def probe_torch() -> TorchProbe:
    try:
        import torch
    except Exception:
        return TorchProbe(cuda=False, mps=False)

    cuda_available = bool(torch.cuda.is_available())
    cuda_name = torch.cuda.get_device_name(0) if cuda_available else None
    mps_backend = getattr(torch.backends, "mps", None)
    mps_available = bool(mps_backend and mps_backend.is_available())
    return TorchProbe(cuda=cuda_available, mps=mps_available, cuda_name=cuda_name)
