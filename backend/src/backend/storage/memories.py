import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.memories import MemoryInput
from backend.storage.versions import create_fact_version


# 新建正式回忆存储文件
def create_memory(
    connection: sqlite3.Connection,
    data: MemoryInput,
) -> dict:
    memory_id = uuid4().hex
    now = datetime.now(UTC).isoformat()

    connection.execute(
        """
        INSERT INTO fact_nodes (
            id, time_text, content, kind, status, created_at, updated_at
        )
        VALUES (?, ?, ?, 'event', 'confirmed', ?, ?)
        """,
        (memory_id, data.time_text, data.content, now, now),
    )
    version_id = create_fact_version(connection)

    return {
        "id": memory_id,
        "revision": 1,
        "fact_version_id": version_id,
    }


def get_memory(
    connection: sqlite3.Connection,
    memory_id: str,
) -> dict | None:
    row = connection.execute(
        """
        SELECT id, time_text, content, revision, created_at, updated_at
        FROM fact_nodes
        WHERE id = ?
        """,
        (memory_id,),
    ).fetchone()
    return dict(row) if row else None