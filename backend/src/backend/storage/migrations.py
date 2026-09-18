import sqlite3
from contextlib import closing
from pathlib import Path

from backend.storage.database import connect
from backend.storage.schema.v001_drafts import STATEMENTS as V001
from backend.storage.schema.v002_facts import STATEMENTS as V002
from backend.storage.schema.v003_versions import STATEMENTS as V003
from backend.storage.schema.v004_branches import STATEMENTS as V004
from backend.storage.schema.v005_events import STATEMENTS as V005
from backend.storage.schema.v006_chapters import STATEMENTS as V006
from backend.storage.schema.v007_reading import STATEMENTS as V007
from backend.storage.schema.v008_tasks import STATEMENTS as V008
from backend.storage.schema.v009_draft_time import STATEMENTS as V009
from backend.storage.schema.v010_memory_revision import STATEMENTS as V010
from backend.storage.schema.v011_memory_position import STATEMENTS as V011
from backend.storage.schema.v012_life_archive import STATEMENTS as V012


MIGRATIONS = [
    V001, V002, V003, V004, V005,
    V006, V007, V008, V009, V010, V011, V012
]


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path, autocommit=True)) as connection:
        connection.execute("PRAGMA journal_mode = WAL")

    with connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]

        if version > len(MIGRATIONS):
            raise RuntimeError("数据库版本高于当前程序支持的版本")

        for index in range(version, len(MIGRATIONS)):
            for statement in MIGRATIONS[index]:
                connection.execute(statement)

            connection.execute(f"PRAGMA user_version = {index + 1}")