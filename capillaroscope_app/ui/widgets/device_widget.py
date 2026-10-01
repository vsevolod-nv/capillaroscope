from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
)


class DeviceWidget(QGroupBox):
    reconnect_requested = Signal()
    pause_toggled = Signal(bool)
    manual_exposure_toggled = Signal(bool)
    exposure_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__("Устройство")

        self._pause_button = QPushButton("Пауза")
        self._pause_button.setCheckable(True)
        self._reconnect_button = QPushButton("Переподключить")
        self._manual_exposure = QCheckBox("Ручная экспозиция")
        self._exposure = QDoubleSpinBox()
        self._exposure.setSuffix(" мс")
        self._exposure.setDecimals(2)
        self._exposure.setKeyboardTracking(False)
        self._exposure.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self._pause_button)
        layout.addWidget(self._reconnect_button)
        layout.addWidget(self._manual_exposure)
        layout.addWidget(self._exposure)

        self._pause_button.toggled.connect(self.pause_toggled.emit)
        self._reconnect_button.clicked.connect(
            lambda _checked=False: self.reconnect_requested.emit()
        )
        self._manual_exposure.toggled.connect(self.manual_exposure_toggled.emit)
        self._exposure.valueChanged.connect(self.exposure_changed.emit)

    @property #баг
    def exposure_value(self) -> float:
        return self._exposure.value()

    def set_paused(self, paused: bool) -> None:
        with QSignalBlocker(self._pause_button):
            self._pause_button.setChecked(paused)
            self._pause_button.setText("Продолжить" if paused else "Пауза")

    def set_manual_exposure(self, manual: bool) -> None:
        with QSignalBlocker(self._manual_exposure):
            self._manual_exposure.setChecked(manual)
        self._exposure.setEnabled(manual)

    def set_exposure_range(self, minimum: float, maximum: float, step: float) -> None:
        with QSignalBlocker(self._exposure):
            self._exposure.setRange(minimum, maximum)
            self._exposure.setSingleStep(step)

    def set_exposure_value(self, value: float) -> None:
        with QSignalBlocker(self._exposure):
            self._exposure.setValue(value)
