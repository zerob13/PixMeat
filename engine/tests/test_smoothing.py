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


def test_skin_smoothing_keeps_strong_edges() -> None:
    height, width = 120, 160
    rng = np.random.default_rng(5)
    image = np.zeros((height, width, 3), dtype=np.float32)
    image[:, : width // 2] = [0.72, 0.48, 0.39]
    image[:, width // 2 :] = [0.86, 0.62, 0.50]
    image = np.clip(image + rng.normal(0, 0.025, image.shape).astype(np.float32), 0, 1)
    skin_mask = np.ones((height, width), dtype=np.float32)

    result = smooth_skin(image, skin_mask, smooth=0.85, texture_keep=0.55)

    left_region = np.s_[20:100, 20 : width // 2 - 10]
    right_region = np.s_[20:100, width // 2 + 10 : width - 20]
    before_texture = (_local_variance(image[left_region]) + _local_variance(image[right_region])) / 2
    after_texture = (_local_variance(result[left_region]) + _local_variance(result[right_region])) / 2
    before_edge = float(np.mean(image[20:100, width // 2 + 2]) - np.mean(image[20:100, width // 2 - 3]))
    after_edge = float(np.mean(result[20:100, width // 2 + 2]) - np.mean(result[20:100, width // 2 - 3]))

    assert after_texture < before_texture * 0.75
    assert after_edge > before_edge * 0.85


def _local_variance(region: np.ndarray) -> float:
    centered = region - np.mean(region, axis=(0, 1), keepdims=True)
    return float(np.var(centered))
