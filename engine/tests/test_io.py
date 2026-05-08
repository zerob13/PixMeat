import numpy as np

from beauty_engine.io import read_image, resize_max_side, write_image


def test_png_roundtrip(tmp_path, portrait_image: np.ndarray) -> None:
    output = tmp_path / "portrait.png"
    write_image(output, portrait_image)
    loaded = read_image(output)
    assert loaded.width == portrait_image.shape[1]
    assert loaded.height == portrait_image.shape[0]
    assert loaded.rgb.dtype == np.float32


def test_jpeg_quality_write(tmp_path, portrait_image: np.ndarray) -> None:
    output = tmp_path / "portrait.jpg"
    write_image(output, portrait_image, quality=88)
    assert output.exists()
    assert read_image(output).rgb.shape[:2] == portrait_image.shape[:2]


def test_resize_max_side(portrait_image: np.ndarray) -> None:
    resized = resize_max_side(portrait_image, 100)
    assert max(resized.shape[:2]) == 100
