import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.memories import MemoryInput


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
            id, time_text, content, kind, status,
            created_at, updated_at, position
        )
        VALUES (
            ?, ?, ?, 'event', 'confirmed', ?, ?,
            (
                SELECT COALESCE(MAX(position), 0) + 1
                FROM fact_nodes
                WHERE status = 'confirmed'
            )
        )
        """,
        (memory_id, data.time_text, data.content, now, now),
    )

    return {"id": memory_id, "revision": 1}


def get_memory(
    connection: sqlite3.Connection,
    memory_id: str,
) -> dict | None:
    row = connection.execute(
        """
        SELECT id, time_text, content, position,
               revision, created_at, updated_at
        FROM fact_nodes
        WHERE id = ? AND status = 'confirmed'
        """,
        (memory_id,),
    ).fetchone()
    return dict(row) if row else None


def list_memories(
    connection: sqlite3.Connection,
    query: str = "",
) -> list[dict]:
    query = query.strip()
    rows = connection.execute(
        """
        SELECT id, time_text, content, position,
               revision, created_at, updated_at
        FROM fact_nodes
        WHERE status = 'confirmed'
          AND (
              instr(time_text, ?) > 0
              OR instr(content, ?) > 0
          )
        ORDER BY position, id
        """,
        (query, query),
    )
    return [dict(row) for row in rows]


def update_memory(
    connection: sqlite3.Connection,
    memory_id: str,
    data: MemoryInput,
    *,
    expected_revision: int,
) -> dict:
    now = datetime.now(UTC).isoformat()
    result = connection.execute(
        """
        UPDATE fact_nodes
        SET time_text = ?, content = ?,
            revision = revision + 1, updated_at = ?
        WHERE id = ? AND revision = ? AND status = 'confirmed'
        """,
        (
            data.time_text,
            data.content,
            now,
            memory_id,
            expected_revision,
        ),
    )

    if result.rowcount != 1:
        raise ValueError("回忆不存在或版本已变化，请重新读取")

    return {
        "id": memory_id,
        "revision": expected_revision + 1
    }


def delete_memory(
    connection: sqlite3.Connection,
    memory_id: str,
    *,
    expected_revision: int,
) -> None:
    connection.execute(
        "DELETE FROM fact_sources WHERE fact_id = ?",
        (memory_id,),
    )
    result = connection.execute(
        """
        DELETE FROM fact_nodes
        WHERE id = ? AND revision = ? AND status = 'confirmed'
        """,
        (memory_id, expected_revision),
    )

    if result.rowcount != 1:
        raise ValueError("回忆不存在或版本已变化，请重新读取")