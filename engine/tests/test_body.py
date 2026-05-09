import cv2
import numpy as np
import pytest

from beauty_engine.body import apply_body_shape, build_body_handles
from beauty_engine.face import FaceLandmarks
from beauty_engine.params import BodyParams


@pytest.fixture()
def full_body_image() -> np.ndarray:
    image, _face = make_full_body()
    return image


@pytest.fixture()
def full_body_face() -> FaceLandmarks:
    _image, face = make_full_body()
    return face


def test_zero_body_shape_returns_original(full_body_image: np.ndarray, full_body_face: FaceLandmarks) -> None:
    result = apply_body_shape(full_body_image, full_body_face, BodyParams())
    assert np.allclose(result, full_body_image)


def test_body_slim_changes_body_region(full_body_image: np.ndarray, full_body_face: FaceLandmarks) -> None:
    handles = build_body_handles(full_body_image.shape[:2], full_body_face, BodyParams(body_slim=0.55, waist_slim=0.35))
    result = apply_body_shape(full_body_image, full_body_face, BodyParams(body_slim=0.55, waist_slim=0.35))
    diff = np.mean(np.abs(result - full_body_image), axis=2)
    x, y, w, h = full_body_face.bbox
    face_region = np.zeros(full_body_image.shape[:2], dtype=bool)
    face_region[int(y) : int(y + h), int(x) : int(x + w)] = True

    assert float(np.mean(diff[handles.mask > 0.02])) > 0.0005
    assert float(np.mean(diff[face_region])) < float(np.mean(diff[handles.mask > 0.10])) * 0.8


def test_negative_body_shape_changes_body_region(full_body_image: np.ndarray, full_body_face: FaceLandmarks) -> None:
    handles = build_body_handles(full_body_image.shape[:2], full_body_face, BodyParams(body_slim=-0.55, waist_slim=-0.35))
    result = apply_body_shape(full_body_image, full_body_face, BodyParams(body_slim=-0.55, waist_slim=-0.35))
    diff = np.mean(np.abs(result - full_body_image), axis=2)

    assert handles.has_motion
    assert float(np.mean(diff[handles.mask > 0.10])) > 0.0005


def test_body_handles_are_bounded(full_body_image: np.ndarray, full_body_face: FaceLandmarks) -> None:
    handles = build_body_handles(full_body_image.shape[:2], full_body_face, BodyParams(body_slim=0.7, arm_slim=0.5))
    height, width = full_body_image.shape[:2]

    assert handles.source.shape == handles.target.shape
    assert handles.mask.shape == full_body_image.shape[:2]
    assert 0 <= handles.mask.min() <= handles.mask.max() <= 1
    assert np.all(handles.target[:, 0] >= 0)
    assert np.all(handles.target[:, 0] <= width - 1)
    assert np.all(handles.target[:, 1] >= 0)
    assert np.all(handles.target[:, 1] <= height - 1)


def make_full_body(width: int = 260, height: int = 360) -> tuple[np.ndarray, FaceLandmarks]:
    image = np.zeros((height, width, 3), dtype=np.float32)
    image[:, :, :] = (0.25, 0.27, 0.30)
    face_bbox = (width * 0.38, height * 0.12, width * 0.24, height * 0.22)
    from beauty_engine.face import _synthetic_landmarks

    face = FaceLandmarks("face_1", face_bbox, _synthetic_landmarks(face_bbox, width, height), 0.9)
    cv2.ellipse(
        image,
        (int(width * 0.50), int(height * 0.22)),
        (int(width * 0.11), int(height * 0.10)),
        0,
        0,
        360,
        (0.82, 0.58, 0.46),
        -1,
    )
    cv2.ellipse(image, (int(width * 0.50), int(height * 0.20)), (34, 20), 0, 0, 360, (0.08, 0.07, 0.06), -1)
    cv2.rectangle(image, (int(width * 0.28), int(height * 0.36)), (int(width * 0.72), int(height * 0.78)), (0.44, 0.48, 0.55), -1)
    cv2.line(image, (int(width * 0.24), int(height * 0.38)), (int(width * 0.10), int(height * 0.90)), (0.78, 0.54, 0.42), 18)
    cv2.line(image, (int(width * 0.76), int(height * 0.38)), (int(width * 0.90), int(height * 0.90)), (0.78, 0.54, 0.42), 18)
    return image, face
