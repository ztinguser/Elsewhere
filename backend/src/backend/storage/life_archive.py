import sqlite3
from datetime import UTC, datetime


def get_archive(connection: sqlite3.Connection) -> dict:
    row = connection.execute(
        """
        SELECT revision, confirmed_revision, confirmed_at
        FROM life_archive
        WHERE id = 1
        """
    ).fetchone()

    archive = dict(row)
    archive["is_confirmed"] = (
        archive["revision"] == archive["confirmed_revision"]
    )
    return archive


def confirm_archive(
    connection: sqlite3.Connection,
    *,
    expected_revision: int,
) -> dict:
    result = connection.execute(
        """
        UPDATE life_archive
        SET confirmed_revision = revision, confirmed_at = ?
        WHERE id = 1 AND revision = ?
        """,
        (datetime.now(UTC).isoformat(), expected_revision),
    )

    if result.rowcount != 1:
        raise ValueError("真实人生已变化，请重新检查后确认存档")

    return get_archive(connection)


def advance_archive_revision(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE life_archive SET revision = revision + 1 WHERE id = 1"
    )