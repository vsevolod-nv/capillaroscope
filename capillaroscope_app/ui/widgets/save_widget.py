from PySide6.QtWidgets import QGroupBox


class SaveWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Сохранить")
