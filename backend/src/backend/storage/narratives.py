import json
import sqlite3

from backend.models.narrative import NarrativeReview, NarrativeText
from backend.prompts.narrative import VERSION
from backend.storage.chapter_publication import publish_chapter, record_chapter_review
from backend.storage.chapters import get_chapter_version, save_chapter_draft
from backend.storage.stages import get_stage


def get_narrative(connection: sqlite3.Connection, stage_id: str, kind: str) -> dict | None:
    row = connection.execute(
        """SELECT v.id FROM chapters c JOIN chapter_versions v ON v.chapter_id = c.id
           WHERE c.stage_id = ? AND c.kind = ? AND v.status = 'published'""",
        (stage_id, kind),
    ).fetchone()
    return get_chapter_version(connection, row["id"]) if row else None


def require_chapters(connection: sqlite3.Connection, branch_id: str, through: int) -> None:
    missing = connection.execute(
        """SELECT s.id FROM simulation_stages s WHERE s.branch_id = ? AND s.position <= ?
           AND NOT EXISTS (
               SELECT 1 FROM chapters c JOIN chapter_versions v ON v.chapter_id = c.id
               WHERE c.stage_id = s.id AND c.kind = 'chapter' AND v.status = 'published'
           ) LIMIT 1""",
        (branch_id, through),
    ).fetchone()
    if missing:
        raise ValueError("请先生成并发布此前阶段的文学章节")


def save_narrative_draft(connection, branch_id, position, kind, draft: NarrativeText, reply):
    stage = get_stage(connection, branch_id, position)
    if stage is None:
        raise ValueError("只能为有效阶段生成文学正文")
    if kind not in ("chapter", "today", "retrospective"):
        raise ValueError("文学正文类型不正确")
    if kind != "chapter" and stage["end_reason"] != "target":
        raise ValueError("尚未抵达固定终点")
    require_chapters(connection, branch_id, position - 1 if kind == "chapter" else position)
    chapter_position = position + {"chapter": 0, "today": 1, "retrospective": 2}[kind]
    existing = connection.execute(
        "SELECT stage_id, kind FROM chapters WHERE branch_id = ? AND position = ?",
        (branch_id, chapter_position),
    ).fetchone()
    if existing and (existing["stage_id"] != stage["id"] or existing["kind"] != kind):
        raise ValueError("章节位置已被其他内容使用")
    version_id = save_chapter_draft(
        connection, branch_id=branch_id, position=chapter_position,
        title=draft.title, paragraphs=draft.paragraphs,
    )
    connection.execute(
        "UPDATE chapters SET stage_id = ?, kind = ? WHERE branch_id = ? AND position = ?",
        (stage["id"], kind, branch_id, chapter_position),
    )
    connection.execute(
        "UPDATE chapter_versions SET outline = ?, prompt_version = ?, generation = ? WHERE id = ?",
        (json.dumps(draft.outline, ensure_ascii=False), VERSION,
         json.dumps({"model": reply.model, "usage": reply.usage}), version_id),
    )
    return version_id


def finish_narrative(connection, version_id, review: NarrativeReview, reply):
    connection.execute(
        "UPDATE chapter_versions SET review = ? WHERE id = ?",
        (json.dumps({**review.model_dump(), "model": reply.model, "usage": reply.usage},
                    ensure_ascii=False), version_id),
    )
    record_chapter_review(connection, version_id, approved=not review.issues)
    if not review.issues:
        publish_chapter(connection, version_id)


def list_narratives(connection, branch_id: str) -> list[dict]:
    rows = connection.execute(
        """SELECT c.id, c.position, c.kind, c.stage_id, s.position AS stage_position,
                  choice.id AS choice_id, v.id AS version_id
           FROM chapters c JOIN chapter_versions v ON v.chapter_id = c.id
           LEFT JOIN simulation_stages s ON s.id = c.stage_id
           LEFT JOIN simulation_choices choice ON choice.stage_id = s.id
           WHERE c.branch_id = ? AND v.status = 'published' ORDER BY c.position""",
        (branch_id,),
    ).fetchall()
    result = []
    for row in rows:
        version = get_chapter_version(connection, row["version_id"])
        result.append({
            **dict(row), "title": version["title"], "revision": version["revision"],
            "status": version["status"], "paragraphs": version["paragraphs"],
        })
    return result
