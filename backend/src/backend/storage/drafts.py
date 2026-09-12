import sqlite3
from datetime import UTC, datetime


def save_draft(
    connection: sqlite3.Connection,
    draft_id: str,
    content: str,
    *,
    expected_revision: int,
) -> int:
    now = datetime.now(UTC).isoformat()

    if expected_revision == 0:
        result = connection.execute(
            """
            INSERT INTO drafts (id, content, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
            """,
            (draft_id, content, now, now),
        )
    else:
        result = connection.execute(
            """
            UPDATE drafts
            SET content = ?, revision = revision + 1, updated_at = ?
            WHERE id = ? AND revision = ?
            """,
            (content, now, draft_id, expected_revision),
        )

    if result.rowcount != 1:
        raise ValueError("草稿不存在或版本已变化，请重新读取")

    return expected_revision + 1


def get_draft(
    connection: sqlite3.Connection, draft_id: str
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()
    return dict(row) if row else None