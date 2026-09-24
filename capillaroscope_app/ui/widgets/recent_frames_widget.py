from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel


class PhotoLabel(QLabel):
    def __init__(self, path: Path) -> None:
        super().__init__(alignment=Qt.AlignmentFlag.AlignCenter)
        self._path = path
        self._pixmap: QPixmap | None = None
        self.setFixedSize(144, 110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_hovered(False)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            logger.info("Opening photo: {}", self._path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path)))
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        self._set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered(False)
        super().leaveEvent(event)

    def set_source_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._set_hovered(False)

    def _set_hovered(self, hovered: bool) -> None:
        self.setStyleSheet(
            "QLabel { border: 2px solid #B0C4DE; background: #eaf3ff; }"
            if hovered
            else "QLabel { border: 2px solid transparent; background: transparent; }"
        )
        if self._pixmap is None:
            return

        width, height = (132, 99) if hovered else (120, 90)
        self.setPixmap(
            self._pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class RecentFramesWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Последние кадры")
        self._layout = QGridLayout(self)

    def set_photos(self, paths: list[Path]) -> None:
        while item := self._layout.takeAt(0):
            if widget := item.widget():
                widget.deleteLater()

        for index, path in enumerate(paths):
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                logger.warning("Could not load photo preview: {}", path)
                continue

            label = PhotoLabel(path)
            label.set_source_pixmap(pixmap)
            self._layout.addWidget(label, index // 4, index % 4)
            logger.debug("Photo preview shown: {}", path)
