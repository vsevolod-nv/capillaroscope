from PySide6.QtWidgets import QGroupBox


class ProcessingWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Обработка")
