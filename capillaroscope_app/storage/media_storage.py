from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2

from capillaroscope_app.domain.models import Frame


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MediaStorage:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self._project_root = project_root

        self._photos_dir = project_root / "media" / "captures" / "photos"
        self._videos_dir = project_root / "media" / "captures" / "videos"

        self._photos_dir.mkdir(parents=True, exist_ok=True)
        self._videos_dir.mkdir(parents=True, exist_ok=True)

        self._db_path = project_root / "media" / "capillaroscope.sqlite3"
        self._connection = sqlite3.connect(self._db_path)

        self._create_tables()

        self._video_writer: cv2.VideoWriter | None = None
        self._video_path: Path | None = None
        self._video_started_at: datetime | None = None
        self._video_started_monotonic: float | None = None
        self._video_size: tuple[int, int] | None = None

    @property
    def is_recording(self) -> bool:
        return self._video_writer is not None

    def _create_tables(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                captured_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL
            );
            """
        )
        self._connection.commit()

    def save_photo(self, frame: Frame) -> Path:
        captured_at = frame.timestamp.astimezone(timezone.utc)

        filename = (
            f"photo_{captured_at.strftime('%Y%m%dT%H%M%S_%f')}_"
            f"{uuid4().hex[:8]}.png"
        )
        photo_path = self._photos_dir / filename

        bgr_image = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
        encoded, image_buffer = cv2.imencode(".png", bgr_image)

        if not encoded:
            raise RuntimeError("Не удалось закодировать фотографию")

        photo_path.write_bytes(image_buffer.tobytes())

        try:
            self._connection.execute(
                """
                INSERT INTO photos (path, captured_at)
                VALUES (?, ?)
                """,
                (
                    self._relative_path(photo_path),
                    captured_at.isoformat(),
                ),
            )
            self._connection.commit()
        except Exception:
            photo_path.unlink(missing_ok=True)
            raise

        return photo_path

    def start_video(self, frame: Frame, fps: float = 30.0) -> Path:
        if self.is_recording:
            raise RuntimeError("Запись видео уже запущена")

        height, width = frame.image.shape[:2]
        started_at = datetime.now(timezone.utc)

        filename = (
            f"video_{started_at.strftime('%Y%m%dT%H%M%S_%f')}_"
            f"{uuid4().hex[:8]}.mp4"
        )
        video_path = self._videos_dir / filename

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            fps,
            (width, height),
        )

        if not writer.isOpened():
            writer.release()
            raise RuntimeError(
                "Не удалось открыть видеофайл. "
                "Проверь поддержку кодека mp4v и путь к проекту."
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
            raise RuntimeError(
                "Во время записи изменилось разрешение камеры"
            )

        bgr_image = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
        self._video_writer.write(bgr_image)

    def stop_video(self) -> Path | None:
        if self._video_writer is None:
            return None

        writer = self._video_writer
        video_path = self._video_path
        started_at = self._video_started_at
        started_monotonic = self._video_started_monotonic

        self._video_writer = None
        self._video_path = None
        self._video_started_at = None
        self._video_started_monotonic = None
        self._video_size = None

        writer.release()

        if (
            video_path is None
            or started_at is None
            or started_monotonic is None
        ):
            raise RuntimeError("Не найдены данные текущей видеозаписи")

        ended_at = datetime.now(timezone.utc)
        duration_seconds = time.monotonic() - started_monotonic

        self._connection.execute(
            """
            INSERT INTO videos (
                path,
                started_at,
                ended_at,
                duration_seconds
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                self._relative_path(video_path),
                started_at.isoformat(),
                ended_at.isoformat(),
                duration_seconds,
            ),
        )
        self._connection.commit()

        return video_path

    def close(self) -> None:
        try:
            if self.is_recording:
                self.stop_video()
        finally:
            self._connection.close()

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self._project_root).as_posix()