from PySide6.QtWidgets import QGroupBox


class PatientCardWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Пациент")
