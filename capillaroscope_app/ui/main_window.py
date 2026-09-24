from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from capillaroscope_app.application.preview_service import PreviewService
from capillaroscope_app.domain.models import Frame
from capillaroscope_app.hardware.camera_base import CameraError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera
from capillaroscope_app.storage.media_storage import MediaStorage
from capillaroscope_app.ui.widgets.analysis_widget import AnalysisWidget
from capillaroscope_app.ui.widgets.camera_preview_widget import CameraPreviewWidget
from capillaroscope_app.ui.widgets.capture_controls_widget import (
    CaptureControlsWidget,
)
from capillaroscope_app.ui.widgets.device_widget import DeviceWidget
from capillaroscope_app.ui.widgets.eye_selector_widget import EyeSelectorWidget
from capillaroscope_app.ui.widgets.medical_card_widget import MedicalCardWidget
from capillaroscope_app.ui.widgets.patient_card_widget import PatientCardWidget
from capillaroscope_app.ui.widgets.previous_series_widget import PreviousSeriesWidget
from capillaroscope_app.ui.widgets.processing_widget import ProcessingWidget
from capillaroscope_app.ui.widgets.recent_frames_widget import RecentFramesWidget
from capillaroscope_app.ui.widgets.save_widget import SaveWidget
from capillaroscope_app.ui.widgets.status_widget import StatusWidget
from capillaroscope_app.ui.widgets.top_bar_widget import TopBarWidget
from capillaroscope_app.ui.widgets.visit_card_widget import VisitCardWidget


class MainWindow(QMainWindow):
    def __init__(self, camera) -> None:
        super().__init__()
        self.setWindowTitle("Capillaroscope Preview")

        self._preview_service = PreviewService(camera)
        self._storage = MediaStorage()
        self._last_frame: Frame | None = None
        self._storage_message = ""

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._update_frame)

        self._camera_preview = CameraPreviewWidget()
        self._capture_controls = CaptureControlsWidget()
        self._device = DeviceWidget()
        self._recent_frames = RecentFramesWidget()
        self._status = StatusWidget()

        self._capture_controls.photo_requested.connect(self._take_photo)
        self._capture_controls.recording_toggled.connect(self._toggle_recording)
        self._device.reconnect_requested.connect(self._reconnect)
        self._device.pause_toggled.connect(self._toggle_pause)
        self._device.manual_exposure_toggled.connect(self._toggle_manual_exposure)
        self._device.exposure_changed.connect(self._change_exposure)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)
        root_layout.addWidget(TopBarWidget())

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        left_container = QWidget()
        left_container.setMinimumWidth(280)
        left_container.setMaximumWidth(340)

        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        left_layout.addWidget(PatientCardWidget())
        left_layout.addWidget(VisitCardWidget())
        left_layout.addWidget(MedicalCardWidget())
        left_layout.addWidget(EyeSelectorWidget())
        left_layout.addWidget(PreviousSeriesWidget(), 1)

        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_layout.addWidget(self._camera_preview, 4)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.addWidget(self._recent_frames, 2)
        bottom_layout.addWidget(AnalysisWidget(), 1)
        center_layout.addLayout(bottom_layout, 1)

        right_container = QWidget()
        right_container.setMinimumWidth(300)
        right_container.setMaximumWidth(360)

        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.addWidget(self._device)
        right_layout.addWidget(self._capture_controls)
        right_layout.addWidget(ProcessingWidget())
        right_layout.addWidget(SaveWidget())
        right_layout.addStretch(1)
        right_layout.addWidget(self._status)

        body_layout.addWidget(left_container)
        body_layout.addWidget(center_container, 1)
        body_layout.addWidget(right_container)

        root_layout.addLayout(body_layout, 1)
        self.setCentralWidget(root)

        self._sync_exposure_controls()
        self._refresh_recent_frames()
        self._update_status()
        self._timer.start()

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

        self._camera_preview.set_frame(frame)
        self._update_status()

    def _take_photo(self) -> None:
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

    def _refresh_recent_frames(self) -> None:
        self._recent_frames.set_photos(self._storage.list_recent_photo_paths())

    def _toggle_recording(self, recording: bool) -> None:
        if not recording:
            self._finish_recording()
        elif self._last_frame is None:
            self._capture_controls.set_recording(False)
            self._storage_message = "Кадр от камеры ещё не получен"
        else:
            try:
                path = self._storage.start_video(self._last_frame)
                self._capture_controls.set_recording(True)
                self._storage_message = f"Запись видео: {path.name}"
            except Exception as exc:
                self._capture_controls.set_recording(False)
                self._storage_message = f"Ошибка запуска видео: {exc}"
        self._update_status()

    def _finish_recording(self) -> None:
        try:
            path = self._storage.stop_video()
            if path is not None:
                self._storage_message = f"Видео сохранено: {path.name}"
        except Exception as exc:
            self._storage_message = f"Ошибка сохранения видео: {exc}"
        finally:
            self._capture_controls.set_recording(False)

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
        self._status.set_status(" | ".join(parts))

    def _reconnect(self) -> None:
        self._finish_recording()
        self._timer.stop()
        self._preview_service.close()
        self._preview_service.restart(create_preview_camera())
        self._device.set_paused(False)
        self._sync_exposure_controls()
        self._update_status()
        self._timer.start()

    def _toggle_pause(self, paused: bool) -> None:
        if paused:
            self._finish_recording()
            self._timer.stop()
            self._preview_service.stop()
        else:
            self._preview_service.start()
            self._timer.start()
        self._device.set_paused(paused)
        self._update_status()

    def _sync_exposure_controls(self) -> None:
        self._device.set_exposure_range(*self._preview_service.get_exposure_range_ms())
        exposure = self._preview_service.get_exposure_ms()
        if exposure is not None:
            self._device.set_exposure_value(exposure)

    def _toggle_manual_exposure(self, manual: bool) -> None:
        self._preview_service.set_auto_exposure(not manual)
        self._device.set_manual_exposure(manual)
        if manual:
            self._preview_service.set_exposure_ms(self._device.exposure_value)
        else:
            self._sync_exposure_controls()

    def _change_exposure(self, exposure_ms: float) -> None:
        self._preview_service.set_exposure_ms(exposure_ms)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        try:
            self._storage.close()
        finally:
            self._preview_service.close()
        super().closeEvent(event)
