import sqlite3
from datetime import datetime

from loguru import logger


class MediaRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add_photo(self, path: str, captured_at: datetime) -> None:
        self._connection.execute(
            "INSERT INTO photos (path, captured_at) VALUES (?, ?)",
            (path, captured_at.isoformat()),
        )
        self._connection.commit()
        logger.info("Photo record added to database: {}", path)

    def list_recent_photo_paths(self, limit: int = 8) -> list[str]:
        cursor = self._connection.execute(
            "SELECT path FROM photos ORDER BY captured_at DESC LIMIT ?",
            (limit,),
        )
        paths = [row[0] for row in cursor.fetchall()]
        logger.debug("Loaded {} recent photo paths from database", len(paths))
        return paths

    def add_video(
        self,
        path: str,
        started_at: datetime,
        ended_at: datetime,
        duration_seconds: float,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO videos (path, started_at, ended_at, duration_seconds)
            VALUES (?, ?, ?, ?)
            """,
            (
                path,
                started_at.isoformat(),
                ended_at.isoformat(),
                duration_seconds,
            ),
        )
        self._connection.commit()
