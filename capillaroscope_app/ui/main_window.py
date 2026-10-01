from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from capillaroscope_app.application.camera_controller import CameraController
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

        self._camera_preview = CameraPreviewWidget()
        self._capture_controls = CaptureControlsWidget()
        self._device = DeviceWidget()
        self._recent_frames = RecentFramesWidget()
        self._status = StatusWidget()
        self._camera_controller = CameraController(camera, self)

        self._connect_controller()
        self._build_layout()
        self._camera_controller.start()

    def _connect_controller(self) -> None:
        self._capture_controls.photo_requested.connect(
            self._camera_controller.take_photo
        )
        self._capture_controls.recording_toggled.connect(
            self._camera_controller.toggle_recording
        )
        self._device.reconnect_requested.connect(self._camera_controller.reconnect)
        self._device.pause_toggled.connect(self._camera_controller.toggle_pause)
        self._device.manual_exposure_toggled.connect(
            self._device.set_manual_exposure
        )  # баг
        self._device.manual_exposure_toggled.connect(
            lambda manual: self._camera_controller.toggle_manual_exposure(
                manual,
                self._device.exposure_value,
            )
        )
        self._device.exposure_changed.connect(self._camera_controller.change_exposure)

        self._camera_controller.frame_ready.connect(self._camera_preview.set_frame)
        self._camera_controller.status_changed.connect(self._status.set_status)
        self._camera_controller.recent_photos_changed.connect(
            self._recent_frames.set_photos
        )
        self._camera_controller.recording_changed.connect(
            self._capture_controls.set_recording
        )
        self._camera_controller.paused_changed.connect(self._device.set_paused)
        self._camera_controller.exposure_range_changed.connect(
            self._device.set_exposure_range
        )
        self._camera_controller.exposure_value_changed.connect(
            self._device.set_exposure_value
        )

    def _build_layout(self) -> None:
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

    def closeEvent(self, event) -> None:
        try:
            self._camera_controller.close()
        finally:
            super().closeEvent(event)
