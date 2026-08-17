from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import CameraBase


class PreviewService:
    def __init__(self, camera: CameraBase) -> None:
        self._camera = camera

    def start(self) -> None:
        self._camera.start_preview()

    def stop(self) -> None:
        self._camera.stop_preview()

    def close(self) -> None:
        try:
            self._camera.stop_preview()
        finally:
            self._camera.disconnect()

    def restart(self, camera: CameraBase) -> None:
        self.close()
        self._camera = camera
        self._camera.start_preview()

    def next_frame(self) -> Frame:
        return self._camera.capture_frame()

    def get_status(self) -> CameraStatus:
        return self._camera.get_status()

    def set_auto_exposure(self, enabled: bool) -> None:
        self._camera.set_auto_exposure(enabled)

    def set_exposure_ms(self, exposure_ms: float) -> None:
        self._camera.set_exposure_ms(exposure_ms)

    def get_exposure_ms(self) -> float | None:
        return self._camera.get_exposure_ms()

    def get_exposure_range_ms(self) -> tuple[float, float, float]:
        return self._camera.get_exposure_range_ms()
