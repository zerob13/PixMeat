from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration for Analysis V2 model loading and debug export."""

    version: str = "v1"
    debug: bool = False
    debug_dir: str | None = None
    device: str = "auto"
    model_paths: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None, *, base: "AnalysisConfig | None" = None) -> "AnalysisConfig":
        defaults = base or cls.from_env()
        payload = payload or {}
        analysis = payload.get("analysis", payload)
        if analysis is None:
            analysis = {}
        model_paths = dict(defaults.model_paths)
        model_paths.update({key: str(value) for key, value in (analysis.get("model_paths") or {}).items() if value})
        return cls(
            version=str(analysis.get("version", defaults.version)),
            debug=_bool(analysis.get("debug", defaults.debug)),
            debug_dir=str(analysis.get("debug_dir", defaults.debug_dir)) if analysis.get("debug_dir", defaults.debug_dir) else None,
            device=str(analysis.get("device", defaults.device)),
            model_paths=model_paths,
        ).normalized()

    @classmethod
    def from_env(cls) -> "AnalysisConfig":
        model_dir = os.environ.get("BEAUTY_ENGINE_MODEL_DIR") or os.environ.get("PIXMEAT_MODEL_DIR")
        paths: dict[str, str] = {}
        if model_dir:
            root = Path(model_dir)
            candidates = {
                "face_detector": ["face_detector.onnx", "scrfd.onnx", "retinaface.onnx"],
                "face_landmarker": ["face_landmarker.task"],
                "person_segmentation": ["person_segmentation.onnx", "selfie_segmenter.task", "modnet.onnx", "birefnet.onnx"],
                "human_parsing": ["human_parsing.onnx", "schp.onnx", "cihp.onnx", "lip.onnx", "atr.onnx"],
            }
            for key, names in candidates.items():
                for name in names:
                    path = root / name
                    if path.exists():
                        paths[key] = str(path)
                        break
        for key in ("face_detector", "face_landmarker", "person_segmentation", "human_parsing"):
            env_value = os.environ.get(f"PIXMEAT_{key.upper()}_MODEL")
            if env_value:
                paths[key] = env_value
        return cls(
            version=os.environ.get("PIXMEAT_ANALYSIS_VERSION", "v1"),
            debug=_bool(os.environ.get("PIXMEAT_ANALYSIS_DEBUG", "false")),
            debug_dir=os.environ.get("PIXMEAT_ANALYSIS_DEBUG_DIR"),
            device=os.environ.get("PIXMEAT_ANALYSIS_DEVICE", "auto"),
            model_paths=paths,
        ).normalized()

    def normalized(self) -> "AnalysisConfig":
        device = self.device if self.device in {"auto", "cpu", "cuda", "mps"} else "auto"
        version = self.version if self.version in {"v1", "v2"} else "v1"
        return AnalysisConfig(
            version=version,
            debug=bool(self.debug),
            debug_dir=self.debug_dir,
            device=device,
            model_paths={key: str(Path(value).expanduser()) for key, value in self.model_paths.items()},
        )

    def resolve_model_path(self, key: str) -> str | None:
        path = self.model_paths.get(key)
        if not path:
            return None
        expanded = Path(path).expanduser()
        return str(expanded) if expanded.exists() else None

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "debug": self.debug,
            "debug_dir": self.debug_dir,
            "device": self.device,
            "model_paths": self.model_paths,
        }


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
