import numpy as np

from beauty_engine.params import EditParams
from beauty_engine.pipeline import process_image


def test_pipeline_zero_params_is_stable(portrait_image: np.ndarray, portrait_face) -> None:
    result = process_image(portrait_image, [portrait_face], "face_1", EditParams.from_payload({}))
    assert result.shape == portrait_image.shape
    assert np.allclose(result, portrait_image)


def test_pipeline_all_groups_changes_image(portrait_image: np.ndarray, portrait_face) -> None:
    params = EditParams.from_cli(
        face_slim=35,
        eye_enlarge=25,
        skin_smooth=45,
        blemish_soften=30,
        skin_tone_even=30,
        brightness=8,
        eye_bright=25,
        teeth_white=20,
        soft_contrast=8,
    )
    result = process_image(portrait_image, [portrait_face], "face_1", params)
    assert result.shape == portrait_image.shape
    assert float(np.mean(np.abs(result - portrait_image))) > 0.002
