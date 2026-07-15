from capillaroscope_app.hardware.mock_camera import MockCamera
from capillaroscope_app.hardware.camera_factory import create_preview_camera


def test_mock_camera_returns_rgb_frame() -> None:
    camera = MockCamera()
    camera.connect()
    camera.start_preview()

    frame = camera.capture_frame()

    assert frame.image.ndim == 3
    assert frame.image.shape[2] == 3
    assert frame.image.dtype.name == "uint8"
    assert camera.get_status().is_mock


def test_camera_factory_can_force_mock(monkeypatch) -> None:
    monkeypatch.setenv("CAPILLAROSCOPE_CAMERA", "mock")

    camera = create_preview_camera()

    assert camera.get_status().is_mock
