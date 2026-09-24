from PySide6.QtWidgets import QGroupBox


class MedicalCardWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Карта")
