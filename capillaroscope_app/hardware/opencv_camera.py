from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import (
    CameraBase,
    CameraCaptureError,
    CameraConnectionError,
)


class OpenCVCamera(CameraBase):
    def __init__(self, index: int = 0) -> None:
        self._index = index
        self._capture: Any | None = None
        self._preview_active = False
        self._last_error: str | None = None

    def connect(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise CameraConnectionError("OpenCV is not installed") from exc

        capture = cv2.VideoCapture(self._index)
        if not capture.isOpened():
            capture.release()
            message = f"OpenCV camera #{self._index} is not available"
            raise CameraConnectionError(message)
        self._capture = capture
        self._last_error = None

    def disconnect(self) -> None:
        self._preview_active = False
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def start_preview(self) -> None:
        if self._capture is None:
            self.connect()
        self._preview_active = True

    def stop_preview(self) -> None:
        self._preview_active = False

    def capture_frame(self) -> Frame:
        if self._capture is None:
            self.connect()
        capture = self._capture
        if capture is None:
            raise CameraCaptureError("OpenCV camera is not connected")
        if not self._preview_active:
            self.start_preview()

        ok, bgr_frame = capture.read()
        if not ok or bgr_frame is None:
            self._last_error = "OpenCV did not return a frame"
            raise CameraCaptureError(self._last_error)

        import cv2

        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        return Frame(
            image=rgb_frame,
            timestamp=datetime.now(timezone.utc),
            camera_name=f"OpenCV camera #{self._index}",
        )

    def get_status(self) -> CameraStatus:
        is_connected = self._capture is not None
        return CameraStatus(
            is_connected=is_connected,
            is_preview_active=self._preview_active,
            camera_name=f"OpenCV camera #{self._index}",
            has_errors=self._last_error is not None,
            error_message=self._last_error,
        )
