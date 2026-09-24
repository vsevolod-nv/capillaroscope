from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout


class CaptureControlsWidget(QGroupBox):
    photo_requested = Signal()
    recording_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__("Захват")

        self._photo_button = QPushButton("Сделать фото")
        self._record_button = QPushButton("Начать запись")
        self._record_button.setCheckable(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._photo_button)
        layout.addWidget(self._record_button)

        self._photo_button.clicked.connect(
            lambda _checked=False: self.photo_requested.emit()
        )
        self._record_button.toggled.connect(self.recording_toggled.emit)

    def set_recording(self, recording: bool) -> None:
        with QSignalBlocker(self._record_button):
            self._record_button.setChecked(recording)
            self._record_button.setText(
                "Остановить запись" if recording else "Начать запись"
            )
