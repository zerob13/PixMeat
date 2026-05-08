from beauty_engine.params import EditParams


def test_default_params_are_valid() -> None:
    params = EditParams.from_payload({})
    assert params.skin.texture_keep == 0.7
    assert params.liquify.face_slim == 0


def test_out_of_range_values_are_clamped() -> None:
    params = EditParams.from_payload(
        {
            "liquify": {"faceSlim": 2, "chinLength": -2},
            "skin": {"textureKeep": 3},
            "beauty": {"brightness": -4},
        }
    )
    assert params.liquify.face_slim == 1
    assert params.liquify.chin_length == -1
    assert params.skin.texture_keep == 1
    assert params.beauty.brightness == -1


def test_cli_values_convert_to_normalized_values() -> None:
    params = EditParams.from_cli(face_slim=30, chin_length=-25, brightness=10)
    assert params.liquify.face_slim == 0.3
    assert params.liquify.chin_length == -0.5
    assert params.beauty.brightness == 0.2
