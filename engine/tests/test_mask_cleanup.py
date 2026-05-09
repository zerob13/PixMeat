from __future__ import annotations

import numpy as np

from beauty_engine.analysis.person_segmentation import cleanup_person_mask, remove_tiny_components


def test_remove_tiny_components_keeps_main_person_blob() -> None:
    binary = np.zeros((80, 80), dtype=np.uint8)
    binary[18:62, 24:56] = 1
    binary[3:6, 3:6] = 1

    cleaned = remove_tiny_components(binary, min_area=200)

    assert cleaned[40, 40] == 1
    assert cleaned[4, 4] == 0


def test_cleanup_person_mask_removes_tiny_components_and_feathers_edges() -> None:
    mask = np.zeros((120, 120), dtype=np.float32)
    mask[30:92, 38:84] = 1.0
    mask[6:10, 6:10] = 1.0

    cleaned = cleanup_person_mask(mask, min_area_ratio=0.01)

    assert cleaned.dtype == np.float32
    assert cleaned[60, 60] > 0.90
    assert cleaned[8, 8] < 0.05
    assert 0.05 < cleaned[28, 60] < 0.95
