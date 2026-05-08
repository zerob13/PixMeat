import numpy as np

from beauty_engine.liquify import apply_liquify
from beauty_engine.masks import build_masks
from beauty_engine.params import LiquifyParams


def test_zero_liquify_returns_original(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    result = apply_liquify(portrait_image, portrait_face, masks, LiquifyParams())
    assert np.allclose(result, portrait_image)


def test_face_slim_changes_face_region(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    result = apply_liquify(portrait_image, portrait_face, masks, LiquifyParams(face_slim=0.45))
    diff = np.mean(np.abs(result - portrait_image), axis=2)
    assert float(np.mean(diff[masks.face > 0.2])) > 0.001
    assert float(np.mean(diff[masks.face < 0.01])) < 0.004


def test_eye_enlarge_changes_eye_region(portrait_image: np.ndarray, portrait_face) -> None:
    masks = build_masks(portrait_image.shape[:2], portrait_face)
    result = apply_liquify(portrait_image, portrait_face, masks, LiquifyParams(eye_enlarge=0.7))
    diff = np.mean(np.abs(result - portrait_image), axis=2)
    assert float(np.mean(diff[masks.eyes > 0.2])) > 0.0005
