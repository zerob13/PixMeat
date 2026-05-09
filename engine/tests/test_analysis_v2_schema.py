from __future__ import annotations

import json

import cv2

from beauty_engine.analysis import AnalysisV2
from beauty_engine.io import to_uint8
from beauty_engine.models.model_config import AnalysisConfig


def test_analysis_v2_result_is_json_serializable(portrait_image) -> None:
    image_bgr = cv2.cvtColor(to_uint8(portrait_image), cv2.COLOR_RGB2BGR)

    result = AnalysisV2(AnalysisConfig(version="v2")).analyze(image_bgr)
    payload = result.to_json()

    json.dumps(payload)
    assert payload["image_size"] == [portrait_image.shape[1], portrait_image.shape[0]]
    assert "person_mask" in payload["masks"]
    assert "skin_final_mask" in payload["masks"]
    assert "face_region" in payload["regions"]
    assert "overall" in payload["confidence"]
