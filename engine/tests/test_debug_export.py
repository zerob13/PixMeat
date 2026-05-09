from __future__ import annotations

import json
from pathlib import Path

import cv2

from beauty_engine.analysis import AnalysisV2
from beauty_engine.io import to_uint8
from beauty_engine.models.model_config import AnalysisConfig


def test_analysis_v2_debug_export_writes_all_artifacts(tmp_path: Path, portrait_image) -> None:
    debug_dir = tmp_path / "analysis_v2"
    image_bgr = cv2.cvtColor(to_uint8(portrait_image), cv2.COLOR_RGB2BGR)

    AnalysisV2(AnalysisConfig(version="v2", debug=True, debug_dir=str(debug_dir))).analyze(image_bgr)

    expected = [
        "01_faces.png",
        "02_face_landmarks.png",
        "03_person_mask.png",
        "04_human_parsing_labels.png",
        "05_skin_semantic_mask.png",
        "06_skin_color_refine_mask.png",
        "07_skin_final_mask.png",
        "08_body_regions.png",
        "09_confidence_map.png",
        "analysis_v2.json",
    ]
    for name in expected:
        assert (debug_dir / name).exists(), name

    payload = json.loads((debug_dir / "analysis_v2.json").read_text(encoding="utf8"))
    assert payload["debug"]["analysis_version"] == "v2"
    assert "model_backends" in payload
