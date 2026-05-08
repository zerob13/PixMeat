import numpy as np

from beauty_engine.beauty import adjust_brightness, apply_beauty
from beauty_engine.masks import build_masks
from beauty_engine.params import BeautyParams


def test_brightness_positive_increases_luminance(portrait_image: np.ndarray) -> None:
    result = adjust_brightness(portrait_image, 0.5)
    assert float(result.mean()) > float(portrait_image.mean())


def test_brightness_negative_decreases_luminance(portrait_image: np.ndarray) -> None:
    result = adjust_brightness(portrait_image, -0.5)
    assert float(result.mean()) < float(portrait_image.mean())


def test_eye_and_teeth_beauty_change_feature_regions(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    result = apply_beauty(portrait_image, masks, BeautyParams(eye_bright=0.8, teeth_white=0.8))
    diff = np.mean(np.abs(result - portrait_image), axis=2)
    assert float(np.mean(diff[(masks.eyes + masks.teeth) > 0.2])) > 0.0005
