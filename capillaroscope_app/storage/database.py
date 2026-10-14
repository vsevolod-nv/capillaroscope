import sqlite3
from pathlib import Path


def connect_database(project_root: Path) -> sqlite3.Connection:
    database_path = project_root / "media" / "capillaroscope.sqlite3"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)

    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.commit()

    return connection
