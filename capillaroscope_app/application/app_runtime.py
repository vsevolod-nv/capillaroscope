from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QMetaObject, QObject, QThread, Qt, Slot

from capillaroscope_app.application.camera_worker import CameraWorker
from capillaroscope_app.application.capture_controller import CaptureController
from capillaroscope_app.storage.storage_worker import StorageWorker


class AppRuntime(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._started = False
        self._closing = False
        self._capture_controller = CaptureController(self)

        self._camera_thread = QThread(self)
        self._camera_thread.setObjectName("camera-thread")
        self._camera_worker = CameraWorker()
        self._camera_worker.moveToThread(self._camera_thread)

        self._storage_thread = QThread(self)
        self._storage_thread.setObjectName("storage-thread")
        self._storage_worker = StorageWorker()
        self._storage_worker.moveToThread(self._storage_thread)

        self._connect_workers()

    @property
    def capture_controller(self) -> CaptureController:
        return self._capture_controller

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._storage_thread.start()
        self._camera_thread.start()

    @Slot()
    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._shutdown_worker(self._camera_thread, self._camera_worker)
        self._shutdown_worker(self._storage_thread, self._storage_worker)

    def _connect_workers(self) -> None:
        controller = self._capture_controller

        self._camera_thread.started.connect(self._camera_worker.initialize)
        self._camera_thread.finished.connect(self._camera_worker.deleteLater)
        controller.camera_pause_requested.connect(self._camera_worker.set_paused)
        controller.camera_reconnect_requested.connect(self._camera_worker.reconnect)
        controller.manual_exposure_requested.connect(
            self._camera_worker.set_manual_exposure
        )
        controller.exposure_requested.connect(self._camera_worker.set_exposure)

        self._camera_worker.ready.connect(controller.on_camera_ready)
        self._camera_worker.frame_ready.connect(controller.on_frame)
        self._camera_worker.status_changed.connect(controller.on_camera_status)
        self._camera_worker.error.connect(controller.on_camera_error)
        self._camera_worker.fatal_error.connect(controller.on_camera_fatal_error)
        self._camera_worker.pause_changed.connect(controller.on_camera_pause_changed)
        self._camera_worker.exposure_range_changed.connect(
            controller.on_exposure_range_changed
        )
        self._camera_worker.exposure_value_changed.connect(
            controller.on_exposure_value_changed
        )

        self._storage_thread.started.connect(self._storage_worker.initialize)
        self._storage_thread.finished.connect(self._storage_worker.deleteLater)
        controller.photo_save_requested.connect(self._storage_worker.save_photo)
        controller.recent_photos_requested.connect(
            self._storage_worker.load_recent_photos
        )
        controller.video_start_requested.connect(self._storage_worker.start_video)
        controller.video_frame_requested.connect(self._storage_worker.write_video_frame)
        controller.video_stop_requested.connect(self._storage_worker.stop_video)

        self._storage_worker.ready.connect(controller.on_storage_ready)
        self._storage_worker.photo_saved.connect(controller.on_photo_saved)
        self._storage_worker.recent_photos_loaded.connect(
            controller.on_recent_photos_loaded
        )
        self._storage_worker.video_started.connect(controller.on_video_started)
        self._storage_worker.video_frame_written.connect(
            controller.on_video_frame_written
        )
        self._storage_worker.video_stopped.connect(controller.on_video_stopped)
        self._storage_worker.operation_failed.connect(controller.on_storage_error)

    def _shutdown_worker(self, thread: QThread, worker: QObject) -> None:
        if not thread.isRunning():
            return
        invoked = QMetaObject.invokeMethod(
            worker,
            "shutdown",
            Qt.ConnectionType.BlockingQueuedConnection,
        )
        if not invoked:
            logger.error("Failed to invoke shutdown for {}", thread.objectName())
        thread.quit()
        thread.wait()
