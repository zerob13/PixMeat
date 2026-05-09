from __future__ import annotations

import numpy as np

from beauty_engine.analysis.face_landmarks import map_crop_landmarks_to_original


def test_crop_landmarks_map_to_original_from_normalized_coordinates() -> None:
    crop_bbox = (10.0, 20.0, 80.0, 40.0)
    landmarks = np.array([[0.0, 0.0, 0.0], [0.5, 0.25, 0.0], [1.0, 1.0, 0.0]], dtype=np.float32)

    mapped = map_crop_landmarks_to_original(landmarks, crop_bbox, (200, 120), normalized=True)

    np.testing.assert_allclose(mapped[:, :2], np.array([[10.0, 20.0], [50.0, 30.0], [90.0, 60.0]], dtype=np.float32))


def test_crop_landmarks_map_to_original_from_pixel_coordinates() -> None:
    crop_bbox = (30.0, 12.0, 50.0, 70.0)
    landmarks = np.array([[3.0, 4.0], [45.0, 66.0]], dtype=np.float32)

    mapped = map_crop_landmarks_to_original(landmarks, crop_bbox, (100, 100), normalized=False)

    np.testing.assert_allclose(mapped[:, :2], np.array([[33.0, 16.0], [75.0, 78.0]], dtype=np.float32))
