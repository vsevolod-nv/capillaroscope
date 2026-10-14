from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from capillaroscope_app.hardware.camera_base import CameraBase, CameraError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera


class CameraWorker(QObject):
    ready = Signal()
    frame_ready = Signal(object)
    status_changed = Signal(object)
    error = Signal(str)
    fatal_error = Signal(str)
    pause_changed = Signal(bool)
    exposure_range_changed = Signal(float, float, float)
    exposure_value_changed = Signal(float)

    def __init__(self, frame_interval_ms: int = 33) -> None:
        super().__init__()
        self._frame_interval_ms = frame_interval_ms
        self._camera: CameraBase | None = None
        self._timer: QTimer | None = None

    @Slot()
    def initialize(self) -> None:
        if self._timer is not None:
            return

        self._timer = QTimer(self)
        self._timer.setInterval(self._frame_interval_ms)
        self._timer.timeout.connect(self._capture_frame)

        try:
            self._replace_camera()
        except Exception as exc:
            logger.exception("Failed to initialize camera worker")
            self.fatal_error.emit(str(exc))
            return

        self._timer.start()
        self.ready.emit()

    @Slot(bool)
    def set_paused(self, paused: bool) -> None:
        if self._camera is None or self._timer is None:
            return
        try:
            if paused:
                self._timer.stop()
                self._camera.stop_preview()
            else:
                self._camera.start_preview()
                self._timer.start()
        except Exception as exc:
            logger.exception("Failed to change camera pause state")
            self.fatal_error.emit(str(exc))
            return
        self.pause_changed.emit(paused)
        self.status_changed.emit(self._camera.get_status())

    @Slot()
    def reconnect(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        try:
            self._replace_camera()
        except Exception as exc:
            logger.exception("Failed to reconnect camera")
            self.fatal_error.emit(str(exc))
            return
        if self._timer is not None:
            self._timer.start()
        self.ready.emit()

    @Slot(bool)
    def set_manual_exposure(self, manual: bool) -> None:
        camera = self._camera
        if camera is None:
            return
        try:
            if manual:
                exposure = camera.get_exposure_ms()
                camera.set_auto_exposure(False)
                if exposure is not None:
                    camera.set_exposure_ms(exposure)
                    self.exposure_value_changed.emit(exposure)
            else:
                camera.set_auto_exposure(True)
                self._emit_exposure()
        except Exception as exc:
            logger.exception("Failed to change camera exposure mode")
            self.error.emit(str(exc))

    @Slot(float)
    def set_exposure(self, exposure_ms: float) -> None:
        if self._camera is None:
            return
        try:
            self._camera.set_exposure_ms(exposure_ms)
        except Exception as exc:
            logger.exception("Failed to set camera exposure")
            self.error.emit(str(exc))

    @Slot()
    def shutdown(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        try:
            self._close_camera()
        except Exception:
            logger.exception("Failed to close camera worker")

    @Slot()
    def _capture_frame(self) -> None:
        camera = self._camera
        if camera is None:
            return
        try:
            frame = camera.capture_frame()
        except CameraError as exc:
            logger.exception("Camera preview failed")
            self.error.emit(str(exc))
            try:
                self._close_camera()
                camera = MockCamera(reason=f"Preview failed: {exc}")
                camera.connect()
                camera.start_preview()
                self._camera = camera
                self._emit_camera_info()
                frame = camera.capture_frame()
            except Exception as recovery_exc:
                logger.exception("Failed to recover camera preview")
                if self._timer is not None:
                    self._timer.stop()
                self.fatal_error.emit(str(recovery_exc))
                return
        except Exception as exc:
            logger.exception("Unexpected camera preview failure")
            if self._timer is not None:
                self._timer.stop()
            self.fatal_error.emit(str(exc))
            return

        self.frame_ready.emit(frame)

    def _replace_camera(self) -> None:
        self._close_camera()
        self._camera = create_preview_camera()
        self._camera.start_preview()
        self._emit_camera_info()

    def _emit_camera_info(self) -> None:
        if self._camera is None:
            return
        self.status_changed.emit(self._camera.get_status())
        self._emit_exposure()

    def _emit_exposure(self) -> None:
        if self._camera is None:
            return
        self.exposure_range_changed.emit(*self._camera.get_exposure_range_ms())
        exposure = self._camera.get_exposure_ms()
        if exposure is not None:
            self.exposure_value_changed.emit(exposure)

    def _close_camera(self) -> None:
        camera = self._camera
        self._camera = None
        if camera is None:
            return
        try:
            camera.stop_preview()
        finally:
            camera.disconnect()
