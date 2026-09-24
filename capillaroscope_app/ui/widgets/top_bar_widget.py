from PySide6.QtWidgets import QLabel


class TopBarWidget(QLabel):
    def __init__(self) -> None:
        super().__init__("Капилляроскоп")
        self.setFixedHeight(40)
