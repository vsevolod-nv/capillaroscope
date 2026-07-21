from __future__ import annotations

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from capillaroscope_app.hardware.camera_factory import create_preview_camera
from capillaroscope_app.ui.main_window import MainWindow

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:

    app = QApplication(sys.argv)
    camera = create_preview_camera()
    window = MainWindow(camera)
    window.resize(1120, 780)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
