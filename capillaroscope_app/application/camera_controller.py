from __future__ import annotations

from enum import Enum, auto

import cv2
from PySide6.QtCore import QObject, QTimer, Signal
from loguru import logger

from capillaroscope_app.application.preview_service import PreviewService
from capillaroscope_app.domain.models import Frame
from capillaroscope_app.hardware.camera_base import CameraBase, CameraError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera
from capillaroscope_app.storage.media_storage import (
    MediaStorage,
    PhotoSaveError,
    RecentPhotosLoadError,
)


class CaptureState(Enum):
    PREVIEW = auto()
    RECORDING = auto()
    PAUSED = auto()
    ERROR = auto()


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
        self._state = CaptureState.PAUSED

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._update_frame)

    def start(self) -> None:
        if self._state in (CaptureState.PREVIEW, CaptureState.RECORDING):
            return
        self._sync_exposure_controls()
        self._refresh_recent_frames()
        self._timer.start()
        self._set_state(CaptureState.PREVIEW)

    def take_photo(self) -> None:
        if self._last_frame is None:
            self._storage_message = "No frame has been received from the camera yet"
        else:
            try:
                path = self._storage.save_photo(self._last_frame)
            except PhotoSaveError as exc:
                logger.exception("Failed to save photo")
                self._storage_message = f"Failed to save photo: {exc}"
            except Exception:
                logger.exception("Unexpected error while saving photo")
                self._storage_message = "Unexpected error while saving photo"
            else:
                self._storage_message = f"Фото сохранено: {path.name}"
                try:
                    self._refresh_recent_frames()
                except RecentPhotosLoadError as exc:
                    logger.exception("Failed to refresh recent photos")
                    self._storage_message += f". Failed to refresh gallery: {exc}"
                except Exception:
                    logger.exception("Unexpected error while refreshing recent photos")
                    self._storage_message += ". Unexpected gallery refresh error"
        self._update_status()

    def set_recording_enabled(self, recording: bool) -> None:
        if recording and self._state is not CaptureState.PREVIEW:
            logger.warning("Recording rejected in state {}", self._state.name)
            self._set_state(self._state)
            return
        if not recording:
            self._finish_recording()
        elif self._last_frame is None:
            self._storage_message = "No frame has been received from the camera yet"
            self._set_state(self._state)
        else:
            try:
                path = self._storage.start_video(self._last_frame)
                self._storage_message = f"Запись видео: {path.name}"
                self._set_state(CaptureState.RECORDING)
            except Exception as exc:
                logger.exception("Failed to start video recording")
                self._storage_message = f"Failed to start video recording: {exc}"
                self._set_state(
                    CaptureState.ERROR
                    if self._storage.is_recording
                    else CaptureState.PREVIEW
                )

    def reconnect(self) -> None:
        self._timer.stop()
        self._last_frame = None
        self._storage_message = ""
        if not self._finish_recording():
            return
        try:
            self._preview_service.close()
            self._preview_service.replace_camera(create_preview_camera())
            self._sync_exposure_controls()
            self._timer.start()
        except Exception as exc:
            logger.exception("Failed to reconnect camera")
            self._storage_message = f"Failed to reconnect camera: {exc}"
            self._set_state(CaptureState.ERROR)
        else:
            self._set_state(CaptureState.PREVIEW)

    def toggle_pause(self, paused: bool) -> None:
        if self._state is CaptureState.ERROR or paused == (
            self._state is CaptureState.PAUSED
        ):
            self._set_state(self._state)
            return
        try:
            if paused:
                if not self._finish_recording():
                    return
                self._timer.stop()
                self._preview_service.stop()
            else:
                self._preview_service.start()
                self._timer.start()
        except Exception as exc:
            logger.exception("Failed to change preview pause state")
            self._storage_message = f"Failed to change preview pause state: {exc}"
            self._set_state(CaptureState.ERROR)
        else:
            self._set_state(CaptureState.PAUSED if paused else CaptureState.PREVIEW)

    def toggle_manual_exposure(self, manual: bool) -> None:
        if manual:
            exposure = self._preview_service.get_exposure_ms()
            self._preview_service.set_auto_exposure(False)
            if exposure is not None:
                self._preview_service.set_exposure_ms(exposure)
                self.exposure_value_changed.emit(exposure)
        else:
            self._preview_service.set_auto_exposure(True)
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
        if self._state not in (CaptureState.PREVIEW, CaptureState.RECORDING):
            return
        try:
            frame = self._preview_service.next_frame()
        except CameraError as exc:
            logger.exception("Camera preview failed")
            reason = str(exc) if self._state is CaptureState.RECORDING else None
            if not self._finish_recording(interrupted_reason=reason):
                return
            try:
                self._preview_service.replace_camera(
                    MockCamera(reason=f"Preview failed: {exc}")
                )
                self._sync_exposure_controls()
                frame = self._preview_service.next_frame()
            except Exception as recovery_exc:
                logger.exception("Failed to recover camera preview")
                self._storage_message += (
                    f". Failed to recover camera preview: {recovery_exc}"
                )
                self._set_state(CaptureState.ERROR)
                return

        self._last_frame = frame
        if self._state is CaptureState.RECORDING:
            try:
                self._storage.write_video_frame(frame)
            except (RuntimeError, cv2.error) as exc:
                logger.exception("Video frame recording failed")
                self._finish_recording(interrupted_reason=str(exc))

        self.frame_ready.emit(frame)
        self._update_status()

    def _refresh_recent_frames(self) -> None:
        self.recent_photos_changed.emit(self._storage.list_recent_photo_paths())

    def _finish_recording(self, interrupted_reason: str | None = None) -> bool:
        try:
            path = self._storage.stop_video()
            if path is not None:
                if interrupted_reason:
                    self._storage_message = (
                        f"Recording interrupted: {interrupted_reason}. "
                        f"Recorded segment saved: {path.name}"
                    )
                else:
                    self._storage_message = f"Видео сохранено: {path.name}"
            elif interrupted_reason:
                self._storage_message = f"Recording interrupted: {interrupted_reason}"
        except Exception as exc:
            logger.exception("Failed to finish video recording")
            if interrupted_reason:
                self._storage_message = (
                    f"Recording interrupted: {interrupted_reason}. "
                    f"Failed to save video: {exc}"
                )
            else:
                self._storage_message = f"Failed to save video: {exc}"
        finally:
            if self._storage.is_recording:
                self._set_state(CaptureState.ERROR)
            elif self._state is CaptureState.RECORDING:
                self._set_state(CaptureState.PREVIEW)
            else:
                self._set_state(self._state)
        return not self._storage.is_recording

    def _set_state(self, state: CaptureState) -> None:
        self._state = state
        if state is CaptureState.ERROR:
            self._timer.stop()
            self._last_frame = None
        self.recording_changed.emit(state is CaptureState.RECORDING)
        self.paused_changed.emit(state is CaptureState.PAUSED)
        self._update_status()

    def _update_status(self) -> None:
        status = self._preview_service.get_status()
        parts = [
            "MOCK" if status.is_mock else "REAL",
            status.camera_name,
            self._state.name.lower(),
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
