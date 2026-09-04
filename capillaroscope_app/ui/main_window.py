from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from capillaroscope_app.application.preview_service import PreviewService
from capillaroscope_app.domain.models import Frame
from capillaroscope_app.hardware.camera_base import CameraError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera
from capillaroscope_app.storage.media_storage import MediaStorage
from capillaroscope_app.ui.control_panel import ControlPanel


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

        self._preview_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(640, 480)
        self._preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._status_label = QLabel()
        self._status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._controls = ControlPanel()
        self._controls.photo_requested.connect(self._take_photo)
        self._controls.recording_toggled.connect(self._toggle_recording)
        self._controls.reconnect_requested.connect(self._reconnect)
        self._controls.pause_toggled.connect(self._toggle_pause)
        self._controls.manual_exposure_toggled.connect(self._toggle_manual_exposure)
        self._controls.exposure_changed.connect(self._change_exposure)

        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self._preview_label, 1)
        preview_layout.addWidget(self._status_label)

        layout = QHBoxLayout()
        layout.addWidget(self._controls)
        layout.addLayout(preview_layout, 1)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self._sync_exposure_controls()
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

        self._render_frame(frame)
        self._update_status()

    def _take_photo(self) -> None:
        if self._last_frame is None:
            self._storage_message = "Кадр от камеры ещё не получен"
        else:
            try:
                path = self._storage.save_photo(self._last_frame)
                self._storage_message = f"Фото сохранено: {path.name}"
            except Exception as exc:
                self._storage_message = f"Ошибка сохранения фото: {exc}"
        self._update_status()

    def _toggle_recording(self, recording: bool) -> None:
        if not recording:
            self._finish_recording()
        elif self._last_frame is None:
            self._controls.set_recording(False)
            self._storage_message = "Кадр от камеры ещё не получен"
        else:
            try:
                path = self._storage.start_video(self._last_frame)
                self._controls.set_recording(True)
                self._storage_message = f"Запись видео: {path.name}"
            except Exception as exc:
                self._controls.set_recording(False)
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
            self._controls.set_recording(False)

    def _render_frame(self, frame: Frame) -> None:
        rgb = np.ascontiguousarray(frame.image)
        height, width, channels = rgb.shape
        image = QImage(
            rgb.data,
            width,
            height,
            channels * width,
            QImage.Format.Format_RGB888,
        ).copy()
        self._preview_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

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
        self._status_label.setText(" | ".join(parts))

    def _reconnect(self) -> None:
        self._finish_recording()
        self._timer.stop()
        self._preview_service.close()
        self._preview_service.restart(create_preview_camera())
        self._controls.set_paused(False)
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
        self._controls.set_paused(paused)
        self._update_status()

    def _sync_exposure_controls(self) -> None:
        self._controls.set_exposure_range(
            *self._preview_service.get_exposure_range_ms()
        )
        exposure = self._preview_service.get_exposure_ms()
        if exposure is not None:
            self._controls.set_exposure_value(exposure)

    def _toggle_manual_exposure(self, manual: bool) -> None:
        self._preview_service.set_auto_exposure(not manual)
        self._controls.set_manual_exposure(manual)
        if manual:
            self._preview_service.set_exposure_ms(self._controls.exposure_value)
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
