import sqlite3


def record_chapter_review(
    connection: sqlite3.Connection,
    version_id: str,
    *,
    approved: bool,
) -> None:
    status = "reviewed" if approved else "rejected"
    result = connection.execute(
        """
        UPDATE chapter_versions
        SET status = ?
        WHERE id = ? AND status = 'draft'
        """,
        (status, version_id),
    )
    if result.rowcount != 1:
        raise ValueError("只能为存在的草稿记录复核结果")


def publish_chapter(
    connection: sqlite3.Connection, version_id: str
) -> None:
    version = connection.execute(
        "SELECT chapter_id, status FROM chapter_versions WHERE id = ?",
        (version_id,),
    ).fetchone()

    if version is None:
        raise ValueError("正文版本不存在")
    if version["status"] == "published":
        return
    if version["status"] != "reviewed":
        raise ValueError("只有通过复核的正文才能发布")

    connection.execute(
        """
        UPDATE chapter_versions
        SET status = 'superseded'
        WHERE chapter_id = ? AND status = 'published'
        """,
        (version["chapter_id"],),
    )
    connection.execute(
        "UPDATE chapter_versions SET status = 'published' WHERE id = ?",
        (version_id,),
    )