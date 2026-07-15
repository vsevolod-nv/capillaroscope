from __future__ import annotations

from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import CameraBase


class PreviewService:
    def __init__(self, camera: CameraBase) -> None:
        self._camera = camera

    def start(self) -> None:
        self._camera.start_preview()

    def stop(self) -> None:
        self._camera.stop_preview()

    def restart(self, camera: CameraBase) -> None:
        self._camera.stop_preview()
        self._camera.disconnect()
        self._camera = camera
        self._camera.start_preview()

    def next_frame(self) -> Frame:
        return self._camera.capture_frame()

    def get_status(self) -> CameraStatus:
        return self._camera.get_status()
