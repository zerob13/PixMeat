from pathlib import Path

import pytest

from beauty_engine.api import EngineApi
from beauty_engine.cli import run_process


def test_demo_image_detects_primary_portrait_face(demo_image_path: Path | None) -> None:
    if demo_image_path is None:
        pytest.skip("demo image is not present")

    session = EngineApi().load_image({"image_path": str(demo_image_path), "preview_max_side": 1600})
    faces = session["faces"]

    assert faces
    face = max(faces, key=lambda item: item["bbox"][2] * item["bbox"][3])
    x, y, width, height = face["bbox"]
    preview_width = session["preview_width"]
    preview_height = session["preview_height"]
    center_x = (x + width * 0.5) / preview_width
    center_y = (y + height * 0.5) / preview_height

    assert 0.30 <= center_x <= 0.55
    assert 0.22 <= center_y <= 0.42
    assert 0.15 <= width / preview_width <= 0.30
    assert 0.14 <= height / preview_height <= 0.26


def test_demo_image_processes_with_all_major_groups(tmp_path, demo_image_path: Path | None) -> None:
    if demo_image_path is None:
        pytest.skip("demo image is not present")

    class Args:
        input = str(demo_image_path)
        output = str(tmp_path / "demo_output.jpg")
        face_slim = 30
        jawline = 20
        chin_length = 4
        eye_enlarge = 20
        nose_slim = 16
        smile = 12
        skin_smooth = 40
        texture_keep = 72
        blemish_soften = 20
        skin_tone_even = 20
        brightness = 6
        eye_bright = 15
        teeth_white = 10
        soft_contrast = 5
        debug_dir = str(tmp_path / "debug")

    run_process(Args())
    assert Path(Args.output).exists()
    assert (tmp_path / "debug" / "face_mask.png").exists()
