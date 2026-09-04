from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ControlPanel(QWidget):
    photo_requested = Signal()
    recording_toggled = Signal(bool)
    reconnect_requested = Signal()
    pause_toggled = Signal(bool)
    manual_exposure_toggled = Signal(bool)
    exposure_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(240)

        self._pause_button = QPushButton("Pause")
        self._pause_button.setCheckable(True)
        self._restart_button = QPushButton("Reconnect")
        self._photo_button = QPushButton("Take photo")
        self._record_button = QPushButton("Start video")
        self._record_button.setCheckable(True)
        self._manual_exposure_checkbox = QCheckBox("Ручная экспозиция")
        self._exposure_spinbox = QDoubleSpinBox()
        self._exposure_spinbox.setSuffix(" мс")
        self._exposure_spinbox.setDecimals(2)
        self._exposure_spinbox.setKeyboardTracking(False)
        self._exposure_spinbox.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        self._add_section(layout, "Camera", self._pause_button, self._restart_button)
        self._add_section(layout, "Capture", self._photo_button, self._record_button)
        self._add_section(
            layout,
            "Exposure",
            self._manual_exposure_checkbox,
            self._exposure_spinbox,
        )
        layout.addStretch(1)

        self._photo_button.clicked.connect(
            lambda _checked=False: self.photo_requested.emit()
        )
        self._restart_button.clicked.connect(
            lambda _checked=False: self.reconnect_requested.emit()
        )
        self._record_button.toggled.connect(self.recording_toggled.emit)
        self._pause_button.toggled.connect(self.pause_toggled.emit)
        self._manual_exposure_checkbox.toggled.connect(
            self.manual_exposure_toggled.emit
        )
        self._exposure_spinbox.valueChanged.connect(self.exposure_changed.emit)

    @staticmethod
    def _add_section(layout: QVBoxLayout, title: str, *widgets: QWidget) -> None:
        label = QLabel(title)
        label.setStyleSheet("font-weight: 600")
        layout.addWidget(label)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addSpacing(12)

    @property
    def exposure_value(self) -> float:
        return self._exposure_spinbox.value()

    def set_recording(self, recording: bool) -> None:
        with QSignalBlocker(self._record_button):
            self._record_button.setChecked(recording)
            self._record_button.setText("Stop video" if recording else "Start video")

    def set_paused(self, paused: bool) -> None:
        with QSignalBlocker(self._pause_button):
            self._pause_button.setChecked(paused)
            self._pause_button.setText("Resume" if paused else "Pause")

    def set_manual_exposure(self, manual: bool) -> None:
        with QSignalBlocker(self._manual_exposure_checkbox):
            self._manual_exposure_checkbox.setChecked(manual)
        self._exposure_spinbox.setEnabled(manual)

    def set_exposure_range(self, minimum: float, maximum: float, step: float) -> None:
        with QSignalBlocker(self._exposure_spinbox):
            self._exposure_spinbox.setRange(minimum, maximum)
            self._exposure_spinbox.setSingleStep(step)

    def set_exposure_value(self, value: float) -> None:
        with QSignalBlocker(self._exposure_spinbox):
            self._exposure_spinbox.setValue(value)
