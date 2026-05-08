import numpy as np

from beauty_engine.masks import build_masks


def test_masks_are_soft_and_bounded(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    assert masks.face.shape == portrait_image.shape[:2]
    assert masks.skin.dtype == np.float32
    assert 0 <= masks.skin.min() <= masks.skin.max() <= 1
    assert np.any((masks.face > 0) & (masks.face < 1))


def test_skin_excludes_protected_regions(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    assert masks.skin.sum() < masks.face.sum()
    assert masks.eyes.sum() > 0
    assert masks.mouth.sum() > 0
