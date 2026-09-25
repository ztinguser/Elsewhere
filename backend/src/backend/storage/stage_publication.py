import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.simulation import StageData, StageReview
from backend.storage.branches import get_branch
from backend.storage.events import create_event
from backend.storage.stages import get_stage, list_stages


def publish_stage(
    connection: sqlite3.Connection,
    *,
    branch_id: str,
    position: int,
    data: StageData,
    review: StageReview,
) -> dict:
    existing = get_stage(connection, branch_id, position)
    if existing is not None:
        return existing
    if not review.approved:
        raise ValueError("校验未通过，不能保存阶段")

    branch = get_branch(connection, branch_id)
    if branch is None or branch["status"] != "ready":
        raise ValueError("分支不存在或当前不能继续推演")

    stages = list_stages(connection, branch_id)
    previous = stages[-1] if stages else None
    expected = previous["position"] + 1 if previous else 1
    if position != expected:
        raise ValueError("阶段必须按顺序保存")

    if previous is not None:
        if previous["end_reason"] == "target":
            raise ValueError("已经抵达终点，不能继续推进")
        choice = connection.execute(
            "SELECT decision FROM simulation_choices WHERE stage_id = ?",
            (previous["id"],),
        ).fetchone()
        if choice is None or not (choice["decision"] or "").strip():
            raise ValueError("请先提交上一阶段的决定")

    if data.end_reason == "target" and data.end_time_text != branch["target_date"]:
        raise ValueError("结束时间必须等于分支固定的终点日期")

    stage_id = uuid4().hex
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO simulation_stages (
            id, branch_id, position, end_time_text,
            end_reason, review, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stage_id, branch_id, position, data.end_time_text,
            data.end_reason, review.model_dump_json(), now,
        ),
    )

    last_position = connection.execute(
        "SELECT COALESCE(MAX(position), 0) FROM events WHERE branch_id = ?",
        (branch_id,),
    ).fetchone()[0]
    for index, event in enumerate(data.events, start=last_position + 1):
        event_id = create_event(
            connection, branch_id=branch_id, position=index, data=event,
        )
        connection.execute(
            "UPDATE events SET stage_id = ?, status = 'validated' WHERE id = ?",
            (stage_id, event_id),
        )

    if data.choice is not None:
        connection.execute(
            "INSERT INTO simulation_choices (id, stage_id, data) VALUES (?, ?, ?)",
            (uuid4().hex, stage_id, data.choice.model_dump_json()),
        )

    connection.execute(
        "UPDATE branches SET status = ?, updated_at = ? WHERE id = ?",
        ("completed" if data.end_reason == "target" else "ready", now, branch_id),
    )
    return get_stage(connection, branch_id, position)