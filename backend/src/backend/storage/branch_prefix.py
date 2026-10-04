from uuid import uuid4


def copy_prefix(connection, parent_id: str, branch_id: str, through: int) -> str:
    """阶段在选择之前结束；仅复制到该边界的有效事件及正式正文。"""
    stages = connection.execute(
        "SELECT * FROM simulation_stages WHERE branch_id = ? AND position <= ? ORDER BY position",
        (parent_id, through),
    ).fetchall()
    for stage in stages:
        stage_id, choice_id = uuid4().hex, uuid4().hex
        connection.execute(
            """INSERT INTO simulation_stages
               (id, branch_id, position, end_time_text, end_reason, review, created_at, source_stage_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (stage_id, branch_id, stage["position"], stage["end_time_text"],
             stage["end_reason"], stage["review"], stage["created_at"], stage["id"]),
        )
        events = connection.execute(
            "SELECT * FROM events WHERE stage_id = ? AND status = 'validated' ORDER BY position",
            (stage["id"],),
        ).fetchall()
        connection.executemany(
            """INSERT INTO events (id, branch_id, position, data, status, created_at, stage_id)
               VALUES (?, ?, ?, ?, 'validated', ?, ?)""",
            [(uuid4().hex, branch_id, e["position"], e["data"], e["created_at"], stage_id) for e in events],
        )
        connection.execute(
            """INSERT INTO simulation_choices (id, stage_id, data, decision_input, decision, decided_at)
               SELECT ?, ?, data, decision_input, decision, decided_at
               FROM simulation_choices WHERE stage_id = ?""",
            (choice_id, stage_id, stage["id"]),
        )
        copy_chapter(connection, stage["id"], stage_id, branch_id)
    return choice_id


def copy_chapter(connection, source_stage_id: str, stage_id: str, branch_id: str) -> None:
    source = connection.execute(
        """SELECT c.position, v.* FROM chapters c
           JOIN chapter_versions v ON v.chapter_id = c.id
           WHERE c.stage_id = ? AND c.kind = 'chapter' AND v.status = 'published'""",
        (source_stage_id,),
    ).fetchone()
    chapter_id, version_id = uuid4().hex, uuid4().hex
    connection.execute(
        """INSERT INTO chapters (id, branch_id, position, created_at, stage_id, kind)
           VALUES (?, ?, ?, ?, ?, 'chapter')""",
        (chapter_id, branch_id, source["position"], source["created_at"], stage_id),
    )
    connection.execute(
        """INSERT INTO chapter_versions
           (id, chapter_id, revision, title, status, created_at, outline, review,
            prompt_version, generation, source_version_id)
           VALUES (?, ?, 1, ?, 'published', ?, ?, ?, ?, ?, ?)""",
        (version_id, chapter_id, source["title"], source["created_at"], source["outline"],
         source["review"], source["prompt_version"], source["generation"], source["id"]),
    )
    paragraphs = connection.execute(
        "SELECT position, content FROM paragraphs WHERE version_id = ? ORDER BY position",
        (source["id"],),
    ).fetchall()
    connection.executemany(
        "INSERT INTO paragraphs (id, version_id, position, content) VALUES (?, ?, ?, ?)",
        [(uuid4().hex, version_id, p["position"], p["content"]) for p in paragraphs],
    )
