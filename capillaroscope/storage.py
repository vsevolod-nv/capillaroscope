from pathlib import Path
import sqlite3


class Storage:
    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = app_dir / "capillaroscope.sqlite3"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        print(f"DB started: {self.db_path}")

    def create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS session (
                id INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS video (
                id INTEGER PRIMARY KEY,
                id_session INTEGER NOT NULL,
                path TEXT NOT NULL,
                FOREIGN KEY (id_session) REFERENCES session(id)
            );

            CREATE TABLE IF NOT EXISTS photo_raw (
                id INTEGER PRIMARY KEY,
                video_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                FOREIGN KEY (video_id) REFERENCES video(id)
            );
            """,
        )
        self.conn.commit()

    def add_demo_data(self):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO session DEFAULT VALUES")
        session_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO video (id_session, path) VALUES (?, ?)",
            (session_id, "files/videos/demo.mp4"),
        )
        video_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO photo_raw (video_id, path) VALUES (?, ?)",
            (video_id, "files/images/demo.png"),
        )
        self.conn.commit()
        message = f"Inserted session={session_id}, video={video_id}"
        print(f"{message}, photo=files/images/demo.png")

    def delete_last_photo(self):
        row = self.conn.execute(
            """
            SELECT photo_raw.id, photo_raw.video_id, video.id_session
            FROM photo_raw
            JOIN video ON video.id = photo_raw.video_id
            ORDER BY photo_raw.id DESC
            LIMIT 1
            """,
        ).fetchone()

        if row is None:
            print("Nothing to delete")
            return

        photo_id, video_id, session_id = row
        self.conn.execute("DELETE FROM photo_raw WHERE id = ?", (photo_id,))
        self.conn.execute("DELETE FROM video WHERE id = ?", (video_id,))
        self.conn.execute("DELETE FROM session WHERE id = ?", (session_id,))
        self.conn.commit()
        print(f"Deleted photo={photo_id}, video={video_id}, session={session_id}")

    def clear_all(self):
        self.conn.execute("DELETE FROM photo_raw")
        self.conn.execute("DELETE FROM video")
        self.conn.execute("DELETE FROM session")
        self.conn.commit()
        print("DB cleared")

    def close(self):
        self.conn.close()
        print("DB stopped")
