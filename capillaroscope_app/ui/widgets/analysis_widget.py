from PySide6.QtWidgets import QGroupBox


class AnalysisWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Анализ и показатели")
