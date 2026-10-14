from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class StatusWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Статус")
        self._label = QLabel()
        self._label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def set_status(self, text: str) -> None:
        self._label.setText(text)
