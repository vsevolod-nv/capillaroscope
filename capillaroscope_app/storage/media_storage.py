import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2
from loguru import logger

from capillaroscope_app.domain.models import Frame
from capillaroscope_app.storage.database import connect_database
from capillaroscope_app.storage.media_repository import MediaRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PhotoSaveError(RuntimeError):
    """Raised when a photo cannot be encoded, written, or registered."""


class RecentPhotosLoadError(RuntimeError):
    """Raised when the recent-photo list cannot be read."""


class MediaStorage:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self._project_root = project_root

        self._photos_dir = project_root / "media" / "captures" / "photos"
        self._videos_dir = project_root / "media" / "captures" / "videos"

        self._photos_dir.mkdir(parents=True, exist_ok=True)
        self._videos_dir.mkdir(parents=True, exist_ok=True)

        self._connection = connect_database(project_root)
        self._repository = MediaRepository(self._connection)

        self._video_writer: cv2.VideoWriter | None = None
        self._video_path: Path | None = None
        self._video_started_at: datetime | None = None
        self._video_started_monotonic: float | None = None
        self._video_size: tuple[int, int] | None = None

    @property
    def is_recording(self) -> bool:
        return self._video_writer is not None

    def save_photo(self, frame: Frame) -> Path:
        captured_at = frame.timestamp.astimezone(timezone.utc)

        filename = (
            f"photo_{captured_at.strftime('%Y%m%dT%H%M%S_%f')}_"
            f"{uuid4().hex[:8]}.png"
        )
        photo_path = self._photos_dir / filename

        try:
            bgr_image = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
            encoded, image_buffer = cv2.imencode(".png", bgr_image)
        except cv2.error as exc:
            raise PhotoSaveError("Failed to process photo image") from exc

        if not encoded:
            raise PhotoSaveError("Failed to encode photo")

        try:
            photo_path.write_bytes(image_buffer.tobytes())
        except OSError as exc:
            raise PhotoSaveError("Failed to write photo file") from exc

        try:
            self._repository.add_photo(
                self._relative_path(photo_path),
                captured_at,
            )
        except sqlite3.Error as exc:
            logger.exception(
                "Failed to add photo record, rolling back transaction: {}",
                photo_path,
            )
            self._connection.rollback()
            photo_path.unlink(missing_ok=True)
            raise PhotoSaveError("Failed to save photo metadata") from exc
        except Exception:
            logger.exception("Failed to save photo metadata: {}", photo_path)
            photo_path.unlink(missing_ok=True)
            raise

        return photo_path

    def list_recent_photo_paths(self, limit: int = 8) -> list[Path]:
        try:
            paths = self._repository.list_recent_photo_paths(limit)
        except sqlite3.Error as exc:
            raise RecentPhotosLoadError("Failed to load recent photos") from exc
        return [self._project_root / path for path in paths]

    def start_video(self, frame: Frame, fps: float = 30.0) -> Path:
        if self.is_recording:
            raise RuntimeError("Video recording is already running")

        height, width = frame.image.shape[:2]
        started_at = datetime.now(timezone.utc)

        filename = (
            f"video_{started_at.strftime('%Y%m%dT%H%M%S_%f')}_" f"{uuid4().hex[:8]}.mp4"
        )
        video_path = self._videos_dir / filename

        fourcc = cv2.VideoWriter.fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            fps,
            (width, height),
        )

        if not writer.isOpened():
            writer.release()
            raise RuntimeError(
                "Failed to open video file. "
                "Check mp4v codec support and the project path."
            )

        self._video_writer = writer
        self._video_path = video_path
        self._video_started_at = started_at
        self._video_started_monotonic = time.monotonic()
        self._video_size = (width, height)

        return video_path

    def write_video_frame(self, frame: Frame) -> None:
        if self._video_writer is None:
            return

        height, width = frame.image.shape[:2]

        if self._video_size != (width, height):
            raise RuntimeError("Camera resolution changed during recording")

        bgr_image = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
        self._video_writer.write(bgr_image)

    def stop_video(self) -> Path | None:
        if self._video_writer is None:
            return None

        writer = self._video_writer
        video_path = self._video_path
        started_at = self._video_started_at
        started_monotonic = self._video_started_monotonic

        writer.release()

        self._video_writer = None
        self._video_path = None
        self._video_started_at = None
        self._video_started_monotonic = None
        self._video_size = None

        if video_path is None or started_at is None or started_monotonic is None:
            raise RuntimeError("Current video recording metadata is missing")

        ended_at = datetime.now(timezone.utc)
        duration_seconds = time.monotonic() - started_monotonic

        self._repository.add_video(
            self._relative_path(video_path),
            started_at,
            ended_at,
            duration_seconds,
        )

        return video_path

    def close(self) -> None:
        try:
            if self.is_recording:
                self.stop_video()
        finally:
            self._connection.close()

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self._project_root).as_posix()
