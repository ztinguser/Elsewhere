import sqlite3
from contextlib import closing
from pathlib import Path

from backend.storage.database import connect
from backend.storage.schema.v001_drafts import STATEMENTS as V001
from backend.storage.schema.v002_facts import STATEMENTS as V002
from backend.storage.schema.v003_versions import STATEMENTS as V003
from backend.storage.schema.v004_branches import STATEMENTS as V004
from backend.storage.schema.v005_events import STATEMENTS as V005


MIGRATIONS = [V001, V002, V003, V004, V005]


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