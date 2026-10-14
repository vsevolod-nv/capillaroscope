from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QImage

from capillaroscope_app.domain.models import Frame
from capillaroscope_app.storage.media_storage import MediaStorage


class StorageWorker(QObject):
    ready = Signal()
    photo_saved = Signal(object)
    recent_photos_loaded = Signal(list)
    video_started = Signal(object)
    video_frame_written = Signal()
    video_stopped = Signal(object)
    operation_failed = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self._storage: MediaStorage | None = None

    @Slot()
    def initialize(self) -> None:
        if self._storage is not None:
            return
        try:
            self._storage = MediaStorage()
        except Exception as exc:
            logger.exception("Failed to initialize storage worker")
            self.operation_failed.emit("initialize", str(exc))
            return
        self.ready.emit()

    @Slot(object)
    def save_photo(self, frame: Frame) -> None:
        if self._storage is None:
            self.operation_failed.emit("save_photo", "Storage is not ready")
            return
        try:
            path = self._storage.save_photo(frame)
        except Exception as exc:
            logger.exception("Failed to save photo")
            self.operation_failed.emit("save_photo", str(exc))
            return
        self.photo_saved.emit(path)

    @Slot()
    def load_recent_photos(self) -> None:
        if self._storage is None:
            self.operation_failed.emit("recent_photos", "Storage is not ready")
            return
        try:
            paths = self._storage.list_recent_photo_paths()
            photos = []
            for path in paths:
                image = QImage(str(path))
                if image.isNull():
                    logger.warning("Could not load photo preview: {}", path)
                    continue
                thumbnail = image.scaled(
                    132,
                    99,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                photos.append((path, thumbnail))
        except Exception as exc:
            logger.exception("Failed to load recent photos")
            self.operation_failed.emit("recent_photos", str(exc))
            return
        self.recent_photos_loaded.emit(photos)

    @Slot(object)
    def start_video(self, frame: Frame) -> None:
        if self._storage is None:
            self.operation_failed.emit("start_video", "Storage is not ready")
            return
        try:
            path = self._storage.start_video(frame)
        except Exception as exc:
            logger.exception("Failed to start video")
            self.operation_failed.emit("start_video", str(exc))
            return
        self.video_started.emit(path)

    @Slot(object)
    def write_video_frame(self, frame: Frame) -> None:
        if self._storage is None:
            self.operation_failed.emit("write_video", "Storage is not ready")
            return
        try:
            self._storage.write_video_frame(frame)
        except Exception as exc:
            logger.exception("Failed to write video frame")
            self.operation_failed.emit("write_video", str(exc))
            return
        self.video_frame_written.emit()

    @Slot()
    def stop_video(self) -> None:
        if self._storage is None:
            self.operation_failed.emit("stop_video", "Storage is not ready")
            return
        try:
            path = self._storage.stop_video()
        except Exception as exc:
            logger.exception("Failed to stop video")
            self.operation_failed.emit("stop_video", str(exc))
            return
        self.video_stopped.emit(path)

    @Slot()
    def shutdown(self) -> None:
        if self._storage is None:
            return
        try:
            self._storage.close()
        except Exception:
            logger.exception("Failed to close storage worker")
        finally:
            self._storage = None
