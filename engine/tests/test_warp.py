import numpy as np

from beauty_engine.warp import apply_translation, identity_maps, masked_blend, mls_similarity_maps, remap


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


def test_mls_identity_maps_are_stable() -> None:
    handles = np.array([[0, 0], [79, 0], [0, 59], [79, 59], [40, 30]], dtype=np.float32)
    map_x, map_y = mls_similarity_maps((60, 80), handles, handles)
    identity_x, identity_y = identity_maps((60, 80))
    assert np.allclose(map_x, identity_x)
    assert np.allclose(map_y, identity_y)


def test_mls_inverse_translation_maps_target_to_source() -> None:
    source = np.array([[0, 0], [79, 0], [0, 59], [79, 59], [40, 30]], dtype=np.float32)
    target = source + np.array([6, -3], dtype=np.float32)
    map_x, map_y = mls_similarity_maps((60, 80), source, target)
    assert abs(float(map_x[30, 40]) - 34.0) < 0.6
    assert abs(float(map_y[30, 40]) - 33.0) < 0.6
