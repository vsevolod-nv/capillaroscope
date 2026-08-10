import importlib
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout

if __package__:
    storage_module = importlib.import_module(".storage", __package__)
else:
    storage_module = importlib.import_module("storage")


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = storage_module.Storage(Path(__file__).resolve().parent)

        self.add_button = QPushButton("Write demo row")
        self.add_button.clicked.connect(self.storage.add_demo_data)

        self.delete_button = QPushButton("Delete last row")
        self.delete_button.clicked.connect(self.storage.delete_last_photo)

        self.clear_button = QPushButton("Clear DB")
        self.clear_button.clicked.connect(self.storage.clear_all)

        layout = QVBoxLayout()
        layout.addWidget(self.add_button)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.clear_button)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.storage.close()
        super().closeEvent(event)


app = QApplication(sys.argv)
window = Window()
window.show()
sys.exit(app.exec())
