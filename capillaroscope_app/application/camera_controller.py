from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from capillaroscope_app.application.preview_service import PreviewService
from capillaroscope_app.domain.models import Frame
from capillaroscope_app.hardware.camera_base import CameraBase, CameraError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera
from capillaroscope_app.storage.media_storage import MediaStorage


class CameraController(QObject):
    frame_ready = Signal(object)
    status_changed = Signal(str)
    recent_photos_changed = Signal(list)
    recording_changed = Signal(bool)
    paused_changed = Signal(bool)
    exposure_range_changed = Signal(float, float, float)
    exposure_value_changed = Signal(float)

    def __init__(self, camera: CameraBase, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._preview_service = PreviewService(camera)
        self._storage = MediaStorage()
        self._last_frame: Frame | None = None
        self._storage_message = ""

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._update_frame)

    def start(self) -> None:
        self._sync_exposure_controls()
        self._refresh_recent_frames()
        self._update_status()
        self._timer.start()

    def take_photo(self) -> None:
        if self._last_frame is None:
            self._storage_message = "Кадр от камеры ещё не получен"
        else:
            try:
                path = self._storage.save_photo(self._last_frame)
                self._refresh_recent_frames()
                self._storage_message = f"Фото сохранено: {path.name}"
            except Exception as exc:
                self._storage_message = f"Ошибка сохранения фото: {exc}"
        self._update_status()

    def toggle_recording(self, recording: bool) -> None:
        if not recording:
            self._finish_recording()
        elif self._last_frame is None:
            self.recording_changed.emit(False)
            self._storage_message = "Кадр от камеры ещё не получен"
        else:
            try:
                path = self._storage.start_video(self._last_frame)
                self.recording_changed.emit(True)
                self._storage_message = f"Запись видео: {path.name}"
            except Exception as exc:
                self.recording_changed.emit(False)
                self._storage_message = f"Ошибка запуска видео: {exc}"
        self._update_status()

    def reconnect(self) -> None:
        self._finish_recording()
        self._timer.stop()
        self._preview_service.close()
        self._preview_service.restart(create_preview_camera())
        self.paused_changed.emit(False)
        self._sync_exposure_controls()
        self._update_status()
        self._timer.start()

    def toggle_pause(self, paused: bool) -> None:
        if paused:
            self._finish_recording()
            self._timer.stop()
            self._preview_service.stop()
        else:
            self._preview_service.start()
            self._timer.start()
        self.paused_changed.emit(paused)
        self._update_status()

    def toggle_manual_exposure(self, manual: bool, exposure_ms: float) -> None:
        self._preview_service.set_auto_exposure(not manual)
        if manual:
            self._preview_service.set_exposure_ms(exposure_ms)
        else:
            self._sync_exposure_controls()

    def change_exposure(self, exposure_ms: float) -> None:
        self._preview_service.set_exposure_ms(exposure_ms)

    def close(self) -> None:
        self._timer.stop()
        try:
            self._storage.close()
        finally:
            self._preview_service.close()

    def _update_frame(self) -> None:
        try:
            frame = self._preview_service.next_frame()
        except CameraError as exc:
            self._finish_recording()
            self._preview_service.restart(MockCamera(reason=f"Preview failed: {exc}"))
            self._sync_exposure_controls()
            frame = self._preview_service.next_frame()

        self._last_frame = frame
        if self._storage.is_recording:
            try:
                self._storage.write_video_frame(frame)
            except RuntimeError as exc:
                self._storage_message = str(exc)
                self._finish_recording()

        self.frame_ready.emit(frame)
        self._update_status()

    def _refresh_recent_frames(self) -> None:
        self.recent_photos_changed.emit(self._storage.list_recent_photo_paths())

    def _finish_recording(self) -> None:
        try:
            path = self._storage.stop_video()
            if path is not None:
                self._storage_message = f"Видео сохранено: {path.name}"
        except Exception as exc:
            self._storage_message = f"Ошибка сохранения видео: {exc}"
        finally:
            self.recording_changed.emit(False)

    def _update_status(self) -> None:
        status = self._preview_service.get_status()
        parts = [
            "MOCK" if status.is_mock else "REAL",
            status.camera_name,
            "preview" if status.is_preview_active else "stopped",
        ]
        if status.error_message:
            parts.append(status.error_message)
        if self._storage_message:
            parts.append(self._storage_message)
        self.status_changed.emit(" | ".join(parts))

    def _sync_exposure_controls(self) -> None:
        self.exposure_range_changed.emit(*self._preview_service.get_exposure_range_ms())
        exposure = self._preview_service.get_exposure_ms()
        if exposure is not None:
            self.exposure_value_changed.emit(exposure)
