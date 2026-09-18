import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.storage.life_archive import get_archive
from backend.storage.memories import list_memories


def create_fact_version(connection: sqlite3.Connection) -> str:
    snapshot = {
        "format_version": 2,
        "archive_revision": get_archive(connection)["revision"],
        "facts": list_memories(connection),
    }

    version_id = uuid4().hex
    connection.execute(
        "INSERT INTO fact_versions (id, snapshot, created_at) VALUES (?, ?, ?)",
        (
            version_id,
            json.dumps(snapshot, ensure_ascii=False),
            datetime.now(UTC).isoformat(),
        ),
    )
    return version_id


def get_fact_version(
    connection: sqlite3.Connection, version_id: str
) -> dict | None:
    row = connection.execute(
        "SELECT snapshot FROM fact_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    return json.loads(row["snapshot"]) if row is not None else None