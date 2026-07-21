from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from capillaroscope_app.application.preview_service import PreviewService
from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import CameraError
from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.hardware.mock_camera import MockCamera


class MainWindow(QMainWindow):
    def __init__(self, camera) -> None:
        super().__init__()
        self.setWindowTitle("Capillaroscope Preview")
        self._preview_service = PreviewService(camera)
        self._timer = QTimer(self)
        self._timer.setInterval(33) # туду: перенести в отдельный конфиг
        self._timer.timeout.connect(self._update_frame)

        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(860, 620)
        self._preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
       
        self._status_label = QLabel()
        self._status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._restart_button = QPushButton("Reconnect")
        self._restart_button.clicked.connect(self._reconnect)

        self._pause_button = QPushButton("Pause")
        self._pause_button.setCheckable(True)
        self._pause_button.clicked.connect(self._toggle_pause)

        controls = QHBoxLayout()
        controls.addWidget(self._restart_button)
        controls.addWidget(self._pause_button)
        controls.addStretch(1)
        
        layout = QVBoxLayout()
        layout.addWidget(self._preview_label, 1)
        layout.addWidget(self._status_label)
        layout.addLayout(controls)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self._update_status()
        self._timer.start()

    def _update_frame(self) -> None:
        try:
            frame = self._preview_service.next_frame()
        except CameraError as exc:
            fallback = MockCamera(reason=f"Preview failed: {exc}")
            fallback.connect()
            fallback.start_preview()
            self._preview_service.restart(fallback)
            self._update_status()
            frame = self._preview_service.next_frame()

        self._render_frame(frame)
        self._update_status()

    def _render_frame(self, frame: Frame) -> None:
        rgb = np.ascontiguousarray(frame.image)
        height, width, channels = rgb.shape
        bytes_per_line = channels * width
        image = QImage(
            rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(image)
        scaled = pixmap.scaled(
            self._preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)

    def _update_status(self) -> None:
        status = self._preview_service.get_status()
        self._status_label.setText(self._format_status(status))

    def _format_status(self, status: CameraStatus) -> str:
        source = "MOCK" if status.is_mock else "REAL"
        state = "preview" if status.is_preview_active else "stopped"
        error = f" | {status.error_message}" if status.error_message else ""
        return f"{source} | {status.camera_name} | {state}{error}"

    def _reconnect(self) -> None:
        self._timer.stop()
        camera = create_preview_camera()
        self._preview_service.restart(camera)
        self._pause_button.setChecked(False)
        self._pause_button.setText("Pause")
        self._update_status()
        self._timer.start()

    def _toggle_pause(self) -> None:
        if self._pause_button.isChecked():
            self._timer.stop()
            self._preview_service.stop()
            self._pause_button.setText("Resume")
        else:
            self._preview_service.start()
            self._timer.start()
            self._pause_button.setText("Pause")
        self._update_status()
