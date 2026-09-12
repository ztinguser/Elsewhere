import sqlite3
from datetime import UTC, datetime


def save_reading_position(
    connection: sqlite3.Connection,
    *,
    branch_id: str,
    paragraph_id: str,
    char_offset: int = 0,
) -> None:
    paragraph = connection.execute(
        """
        SELECT paragraphs.content
        FROM paragraphs
        JOIN chapter_versions ON chapter_versions.id = paragraphs.version_id
        JOIN chapters ON chapters.id = chapter_versions.chapter_id
        WHERE paragraphs.id = ? AND chapters.branch_id = ?
            AND chapter_versions.status IN ('published', 'superseded')
        """,
        (paragraph_id, branch_id),
    ).fetchone()

    if paragraph is None:
        raise ValueError("段落不属于该分支的正式或历史正文")
    if not 0 <= char_offset <= len(paragraph["content"]):
        raise ValueError("阅读位置超出段落范围")

    connection.execute(
        """
        INSERT INTO reading_positions (
            branch_id, paragraph_id, char_offset, updated_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT (branch_id) DO UPDATE SET
            paragraph_id = excluded.paragraph_id,
            char_offset = excluded.char_offset,
            updated_at = excluded.updated_at
        """,
        (
            branch_id,
            paragraph_id,
            char_offset,
            datetime.now(UTC).isoformat(),
        ),
    )


def get_reading_position(
    connection: sqlite3.Connection, branch_id: str
) -> dict | None:
    row = connection.execute(
        """
        SELECT reading_positions.*,
            paragraphs.version_id,
            chapter_versions.chapter_id
        FROM reading_positions
        JOIN paragraphs ON paragraphs.id = reading_positions.paragraph_id
        JOIN chapter_versions ON chapter_versions.id = paragraphs.version_id
        WHERE reading_positions.branch_id = ?
        """,
        (branch_id,),
    ).fetchone()
    return dict(row) if row else None