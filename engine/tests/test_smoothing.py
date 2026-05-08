import numpy as np

from beauty_engine.masks import build_masks
from beauty_engine.params import SkinParams
from beauty_engine.smoothing import apply_skin, smooth_skin


def test_smooth_zero_returns_original(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    result = apply_skin(portrait_image, masks, SkinParams())
    assert np.allclose(result, portrait_image)


def test_skin_smoothing_reduces_variance(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    result = smooth_skin(portrait_image, masks.skin, smooth=0.8, texture_keep=0.45)
    before = np.var(portrait_image[masks.skin > 0.4])
    after = np.var(result[masks.skin > 0.4])
    assert after < before
