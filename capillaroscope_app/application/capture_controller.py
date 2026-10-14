from __future__ import annotations

from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from capillaroscope_app.domain.models import CameraStatus, Frame


class CaptureState(Enum):
    PREVIEW = auto()
    RECORDING = auto()
    PAUSED = auto()
    ERROR = auto()


class CaptureController(QObject):
    frame_ready = Signal(object)
    status_changed = Signal(str)
    recent_photos_changed = Signal(list)
    recording_changed = Signal(bool)
    paused_changed = Signal(bool)
    exposure_range_changed = Signal(float, float, float)
    exposure_value_changed = Signal(float)

    camera_pause_requested = Signal(bool)
    camera_reconnect_requested = Signal()
    manual_exposure_requested = Signal(bool)
    exposure_requested = Signal(float)
    photo_save_requested = Signal(object)
    recent_photos_requested = Signal()
    video_start_requested = Signal(object)
    video_frame_requested = Signal(object)
    video_stop_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._last_frame: Frame | None = None
        self._camera_status = CameraStatus(False, False, "Camera")
        self._storage_message = ""
        self._state = CaptureState.PAUSED
        self._storage_ready = False

        self._recording_start_pending = False
        self._recording_stop_pending = False
        self._video_stop_sent = False
        self._video_write_in_flight = False
        self._dropped_video_frames = 0
        self._pause_after_recording = False
        self._reconnect_after_recording = False

    def take_photo(self) -> None:
        if not self._storage_ready:
            self._storage_message = "Storage is not ready"
        elif self._last_frame is None:
            self._storage_message = "No frame has been received from the camera yet"
        else:
            self._storage_message = "Saving photo..."
            self.photo_save_requested.emit(self._last_frame)
        self._update_status()

    def set_recording_enabled(self, recording: bool) -> None:
        if recording:
            self._start_recording()
        else:
            self._begin_stop_recording()

    def reconnect(self) -> None:
        self._last_frame = None
        if self._recording_is_active_or_pending():
            self._reconnect_after_recording = True
            self._pause_after_recording = False
            self._begin_stop_recording()
            return
        self._storage_message = "Reconnecting camera..."
        self.camera_reconnect_requested.emit()
        self._update_status()

    def toggle_pause(self, paused: bool) -> None:
        if self._state is CaptureState.ERROR:
            self._set_state(self._state)
            return
        if paused and self._recording_is_active_or_pending():
            self._pause_after_recording = True
            self._reconnect_after_recording = False
            self._begin_stop_recording()
            return
        if not paused:
            self._pause_after_recording = False
        self.camera_pause_requested.emit(paused)

    def toggle_manual_exposure(self, manual: bool) -> None:
        self.manual_exposure_requested.emit(manual)

    def change_exposure(self, exposure_ms: float) -> None:
        self.exposure_requested.emit(exposure_ms)

    def _start_recording(self) -> None:
        if (
            self._state is not CaptureState.PREVIEW
            or self._recording_is_active_or_pending()
        ):
            self._set_state(self._state)
            return
        if not self._storage_ready:
            self._storage_message = "Storage is not ready"
        elif self._last_frame is None:
            self._storage_message = "No frame has been received from the camera yet"
        else:
            self._recording_start_pending = True
            self._storage_message = "Starting video recording..."
            self.video_start_requested.emit(self._last_frame)
        self._update_status()

    def _begin_stop_recording(self) -> None:
        if not self._recording_is_active_or_pending():
            self._set_state(self._state)
            return
        self._recording_stop_pending = True
        self._storage_message = "Stopping video recording..."
        self._maybe_request_video_stop()
        self._update_status()

    def _maybe_request_video_stop(self) -> None:
        if (
            not self._recording_stop_pending
            or self._recording_start_pending
            or self._video_write_in_flight
            or self._video_stop_sent
        ):
            return
        self._video_stop_sent = True
        self.video_stop_requested.emit()

    def _recording_is_active_or_pending(self) -> bool:
        return self._state is CaptureState.RECORDING or self._recording_start_pending

    @Slot()
    def on_camera_ready(self) -> None:
        self._storage_message = ""
        self._set_state(CaptureState.PREVIEW)

    @Slot(object)
    def on_frame(self, frame: Frame) -> None:
        self._last_frame = frame
        if self._state is CaptureState.RECORDING and not self._recording_stop_pending:
            if self._video_write_in_flight:
                self._dropped_video_frames += 1
            else:
                self._video_write_in_flight = True
                self.video_frame_requested.emit(frame)
        self.frame_ready.emit(frame)

    @Slot(object)
    def on_camera_status(self, status: CameraStatus) -> None:
        self._camera_status = status
        self._update_status()

    @Slot(str)
    def on_camera_error(self, message: str) -> None:
        self._storage_message = f"Camera error: {message}"
        if self._recording_is_active_or_pending():
            self._begin_stop_recording()
        else:
            self._update_status()

    @Slot(str)
    def on_camera_fatal_error(self, message: str) -> None:
        self._storage_message = f"Camera stopped: {message}"
        if self._recording_is_active_or_pending():
            self._begin_stop_recording()
        self._set_state(CaptureState.ERROR)

    @Slot(bool)
    def on_camera_pause_changed(self, paused: bool) -> None:
        self._set_state(CaptureState.PAUSED if paused else CaptureState.PREVIEW)

    @Slot(float, float, float)
    def on_exposure_range_changed(
        self, minimum: float, maximum: float, step: float
    ) -> None:
        self.exposure_range_changed.emit(minimum, maximum, step)

    @Slot(float)
    def on_exposure_value_changed(self, exposure: float) -> None:
        self.exposure_value_changed.emit(exposure)

    @Slot()
    def on_storage_ready(self) -> None:
        self._storage_ready = True
        self.recent_photos_requested.emit()

    @Slot(list)
    def on_recent_photos_loaded(self, photos: list) -> None:
        self.recent_photos_changed.emit(photos)

    @Slot(object)
    def on_photo_saved(self, path: Path) -> None:
        self._storage_message = f"Photo saved: {path.name}"
        self.recent_photos_requested.emit()
        self._update_status()

    @Slot(object)
    def on_video_started(self, path: Path) -> None:
        self._recording_start_pending = False
        self._dropped_video_frames = 0
        self._storage_message = f"Recording video: {path.name}"
        self._set_state(CaptureState.RECORDING)
        self._maybe_request_video_stop()

    @Slot()
    def on_video_frame_written(self) -> None:
        self._video_write_in_flight = False
        self._maybe_request_video_stop()

    @Slot(object)
    def on_video_stopped(self, path: Path | None) -> None:
        dropped = self._dropped_video_frames
        self._reset_recording_flags()
        if path is not None:
            self._storage_message = f"Video saved: {path.name}"
            if dropped:
                self._storage_message += f"; skipped frames: {dropped}"

        if self._pause_after_recording:
            self._pause_after_recording = False
            self.camera_pause_requested.emit(True)
        elif self._reconnect_after_recording:
            self._reconnect_after_recording = False
            self.camera_reconnect_requested.emit()
        elif self._state is not CaptureState.ERROR:
            self._set_state(CaptureState.PREVIEW)
        else:
            self._update_status()

    @Slot(str, str)
    def on_storage_error(self, operation: str, message: str) -> None:
        self._storage_message = f"Storage error ({operation}): {message}"
        if operation == "initialize":
            self._storage_ready = False
        elif operation == "start_video":
            self._reset_recording_flags()
            if self._state is not CaptureState.ERROR:
                self._set_state(CaptureState.PREVIEW)
            return
        elif operation == "write_video":
            self._video_write_in_flight = False
            self._recording_stop_pending = True
            self._maybe_request_video_stop()
        elif operation == "stop_video":
            self._reset_recording_flags()
            if self._state is not CaptureState.ERROR:
                self._set_state(CaptureState.PREVIEW)
            return
        self._update_status()

    def _reset_recording_flags(self) -> None:
        self._recording_start_pending = False
        self._recording_stop_pending = False
        self._video_stop_sent = False
        self._video_write_in_flight = False
        self._dropped_video_frames = 0

    def _set_state(self, state: CaptureState) -> None:
        self._state = state
        if state is CaptureState.ERROR:
            self._last_frame = None
        self.recording_changed.emit(state is CaptureState.RECORDING)
        self.paused_changed.emit(state is CaptureState.PAUSED)
        self._update_status()

    def _update_status(self) -> None:
        status = self._camera_status
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
