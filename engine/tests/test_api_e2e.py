import json
from pathlib import Path

from beauty_engine.api import EngineApi
from beauty_engine.io import write_image
from beauty_engine.params import EditParams


def test_health_request_returns_ready() -> None:
    api = EngineApi()
    response = api.handle({"id": "1", "method": "health", "params": {}})
    assert response["ok"] is True
    assert response["result"]["status"] == "ready"


def test_unknown_method_returns_error() -> None:
    api = EngineApi()
    response = api.handle({"id": "1", "method": "missing", "params": {}})
    assert response["ok"] is False
    assert response["error"]["code"] == "unknown_method"


def test_load_preview_export_e2e(tmp_path, portrait_image) -> None:
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.jpg"
    write_image(input_path, portrait_image)
    events: list[dict] = []
    api = EngineApi(emit=events.append)

    loaded = api.handle(
        {"id": "load", "method": "load_image", "params": {"image_path": str(input_path), "preview_max_side": 180}}
    )
    assert loaded["ok"] is True
    image_id = loaded["result"]["image_id"]
    assert Path(loaded["result"]["preview_path"]).exists()

    params = EditParams.from_cli(body_slim=20, waist_slim=15, face_slim=30, eye_enlarge=20, skin_smooth=40, brightness=8).to_dict()
    preview = api.handle(
        {
            "id": "preview",
            "method": "render_preview",
            "params": {
                "image_id": image_id,
                "request_token": "preview_test",
                "active_face_id": loaded["result"]["active_face_id"],
                "params": params,
            },
        }
    )
    assert preview["ok"] is True
    assert Path(preview["result"]["preview_result_path"]).exists()

    exported = api.handle(
        {
            "id": "export",
            "method": "export_image",
            "params": {
                "image_id": image_id,
                "job_id": "job_test",
                "active_face_id": loaded["result"]["active_face_id"],
                "output_path": str(output_path),
                "quality": 90,
                "keep_metadata": True,
                "params": params,
            },
        }
    )
    assert exported["ok"] is True
    assert output_path.exists()
    assert any(event["event"] == "job_progress" for event in events)


def test_each_slider_can_render_preview_e2e(tmp_path, portrait_image) -> None:
    input_path = tmp_path / "input.png"
    write_image(input_path, portrait_image)
    api = EngineApi()
    loaded = api.handle(
        {"id": "load", "method": "load_image", "params": {"image_path": str(input_path), "preview_max_side": 180}}
    )
    image_id = loaded["result"]["image_id"]
    active_face_id = loaded["result"]["active_face_id"]
    slider_payloads = [
        {"body": {"body_slim": 0.35}},
        {"body": {"waist_slim": 0.35}},
        {"body": {"arm_slim": 0.35}},
        {"liquify": {"face_slim": 0.35}},
        {"liquify": {"jawline": 0.35}},
        {"liquify": {"chin_length": 0.4}},
        {"liquify": {"eye_enlarge": 0.35}},
        {"liquify": {"nose_slim": 0.35}},
        {"liquify": {"smile": 0.35}},
        {"skin": {"skin_smooth": 0.45}},
        {"skin": {"texture_keep": 0.35, "skin_smooth": 0.45}},
        {"skin": {"blemish_soften": 0.45}},
        {"skin": {"skin_tone_even": 0.45}},
        {"beauty": {"brightness": 0.25}},
        {"beauty": {"eye_bright": 0.45}},
        {"beauty": {"teeth_white": 0.45}},
        {"beauty": {"soft_contrast": 0.25}},
    ]
    for index, params in enumerate(slider_payloads):
        response = api.handle(
            {
                "id": f"preview_{index}",
                "method": "render_preview",
                "params": {
                    "image_id": image_id,
                    "request_token": f"slider_{index}",
                    "active_face_id": active_face_id,
                    "params": params,
                },
            }
        )
        assert response["ok"] is True
        assert Path(response["result"]["preview_result_path"]).exists()


def test_json_protocol_invalid_json_shape() -> None:
    payload = {"id": "x", "ok": False, "error": {"code": "invalid_json"}}
    assert json.dumps(payload)
