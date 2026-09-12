import sqlite3
from datetime import UTC, datetime
from uuid import uuid4


def save_chapter_draft(
    connection: sqlite3.Connection,
    *,
    branch_id: str,
    position: int,
    title: str,
    paragraphs: list[str],
) -> str:
    if not paragraphs or any(not text.strip() for text in paragraphs):
        raise ValueError("正文必须包含非空段落")

    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO chapters (id, branch_id, position, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (branch_id, position) DO NOTHING
        """,
        (uuid4().hex, branch_id, position, now),
    )
    chapter_id = connection.execute(
        "SELECT id FROM chapters WHERE branch_id = ? AND position = ?",
        (branch_id, position),
    ).fetchone()["id"]

    revision = connection.execute(
        """
        SELECT COALESCE(MAX(revision), 0) + 1
        FROM chapter_versions
        WHERE chapter_id = ?
        """,
        (chapter_id,),
    ).fetchone()[0]

    version_id = uuid4().hex
    connection.execute(
        """
        INSERT INTO chapter_versions (
            id, chapter_id, revision, title, created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (version_id, chapter_id, revision, title, now),
    )
    connection.executemany(
        """
        INSERT INTO paragraphs (id, version_id, position, content)
        VALUES (?, ?, ?, ?)
        """,
        [
            (uuid4().hex, version_id, index, text)
            for index, text in enumerate(paragraphs, start=1)
        ],
    )
    return version_id


def get_chapter_version(
    connection: sqlite3.Connection, version_id: str
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM chapter_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    if row is None:
        return None

    version = dict(row)
    version["paragraphs"] = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM paragraphs WHERE version_id = ? ORDER BY position",
            (version_id,),
        )
    ]
    return version


def get_published_chapter(
    connection: sqlite3.Connection, branch_id: str, position: int
) -> dict | None:
    row = connection.execute(
        """
        SELECT chapter_versions.id
        FROM chapter_versions
        JOIN chapters ON chapters.id = chapter_versions.chapter_id
        WHERE chapters.branch_id = ? AND chapters.position = ?
            AND chapter_versions.status = 'published'
        """,
        (branch_id, position),
    ).fetchone()
    return get_chapter_version(connection, row["id"]) if row else None