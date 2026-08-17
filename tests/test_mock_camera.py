from pathlib import Path

import cv2
import numpy as np
import pytest

from capillaroscope_app.hardware import mock_camera as mock_camera_module
from capillaroscope_app.hardware.camera_base import CameraConnectionError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera


def _write_preview_image(directory: Path) -> Path:
    image_path = (
        directory
        / "\u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435"
        / "preview.png"
    )
    bgr_image = np.array([[[10, 20, 30]]], dtype=np.uint8)
    written, encoded_image = cv2.imencode(".png", bgr_image)
    assert written
    image_path.parent.mkdir()
    image_path.write_bytes(encoded_image.tobytes())
    return image_path


def test_mock_camera_returns_rgb_frame(tmp_path: Path) -> None:
    camera = MockCamera(preview_image_path=_write_preview_image(tmp_path))
    camera.connect()
    camera.start_preview()

    frame = camera.capture_frame()

    assert frame.image.ndim == 3
    assert frame.image.shape[2] == 3
    assert frame.image.dtype.name == "uint8"
    assert camera.get_status().is_mock


def test_mock_camera_loads_static_preview_image(tmp_path: Path) -> None:
    image_path = _write_preview_image(tmp_path)
    camera = MockCamera(preview_image_path=image_path)

    frame = camera.capture_frame()

    assert frame.image.tolist() == [[[30, 20, 10]]]
    assert frame.metadata["source"] == "static-image"
    assert frame.metadata["image_path"] == str(image_path)


def test_mock_camera_requires_readable_static_preview(tmp_path: Path) -> None:
    with pytest.raises(CameraConnectionError, match="Could not read"):
        MockCamera(preview_image_path=tmp_path / "missing.jpg")


def test_camera_factory_can_force_mock(tmp_path: Path, monkeypatch) -> None:
    image_path = _write_preview_image(tmp_path)
    monkeypatch.setattr(mock_camera_module, "MOCK_PHOTOS_DIR", image_path.parent)
    monkeypatch.setenv("CAPILLAROSCOPE_CAMERA", "mock")

    camera = create_preview_camera()

    assert camera.get_status().is_mock
    assert camera.capture_frame().metadata["image_path"] == str(image_path)
