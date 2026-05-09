from __future__ import annotations

from pathlib import Path

import cv2

from beauty_engine.analysis import AnalysisV2
from beauty_engine.io import to_uint8
from beauty_engine.models.model_config import AnalysisConfig


def test_missing_model_paths_do_not_crash_analysis(tmp_path: Path, portrait_image) -> None:
    missing = tmp_path / "missing.onnx"
    config = AnalysisConfig(
        version="v2",
        model_paths={
            "face_detector": str(missing),
            "face_landmarker": str(tmp_path / "missing.task"),
            "person_segmentation": str(missing),
            "human_parsing": str(missing),
        },
    )
    image_bgr = cv2.cvtColor(to_uint8(portrait_image), cv2.COLOR_RGB2BGR)

    result = AnalysisV2(config).analyze(image_bgr)

    assert result.confidence.overall >= 0.0
    assert "skin_final_mask" in result.masks
    assert result.regions["torso_region"].source == "geometric"
    assert result.model_backends["face_landmarker"].available is False
    assert result.model_backends["person_segmentation"].source == "fallback"
    assert result.model_backends["human_parsing"].source == "fallback"
