import numpy as np

from beauty_engine.warp import apply_translation, identity_maps, masked_blend, remap


def test_identity_remap_returns_original(portrait_image: np.ndarray) -> None:
    map_x, map_y = identity_maps(portrait_image.shape[:2])
    result = remap(portrait_image, map_x, map_y)
    assert np.allclose(result, portrait_image, atol=1 / 255)


def test_translation_moves_pixels(portrait_image: np.ndarray) -> None:
    result = apply_translation(portrait_image, dx=8, dy=0)
    assert not np.allclose(result, portrait_image)


def test_masked_blend_respects_zero_mask(portrait_image: np.ndarray) -> None:
    mask = np.zeros(portrait_image.shape[:2], dtype=np.float32)
    result = masked_blend(portrait_image, 1 - portrait_image, mask)
    assert np.allclose(result, portrait_image)
