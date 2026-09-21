import json
import sqlite3
from datetime import UTC, datetime


def get_fork_plan(
    connection: sqlite3.Connection,
    branch_id: str,
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM fork_plans WHERE branch_id = ?",
        (branch_id,),
    ).fetchone()
    if row is None:
        return None

    record = dict(row)
    for field in ("initial_result", "final_result", "answers"):
        if record[field] is not None:
            record[field] = json.loads(record[field])
    return record


def save_initial_plan(
    connection: sqlite3.Connection,
    branch_id: str,
    result: dict,
) -> dict:
    plan = result["plan"]
    if plan["blockers"]:
        status = "blocked"
    elif plan["questions"]:
        status = "waiting_input"
    else:
        status = "waiting_confirmation"

    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO fork_plans (
            branch_id, initial_result, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(branch_id) DO NOTHING
        """,
        (
            branch_id,
            json.dumps(result, ensure_ascii=False),
            status,
            now,
            now,
        ),
    )
    return get_fork_plan(connection, branch_id)


def save_answered_plan(
    connection: sqlite3.Connection,
    branch_id: str,
    *,
    answers: list[dict],
    result: dict,
    expected_revision: int,
) -> dict:
    plan = result["plan"]
    if plan["questions"]:
        raise ValueError("整理后的方案不能追加问卷")

    status = "blocked" if plan["blockers"] else "waiting_confirmation"
    updated = connection.execute(
        """
        UPDATE fork_plans
        SET answers = ?, final_result = ?, status = ?,
            revision = revision + 1, updated_at = ?
        WHERE branch_id = ? AND revision = ?
            AND status = 'waiting_input'
        """,
        (
            json.dumps(answers, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            status,
            datetime.now(UTC).isoformat(),
            branch_id,
            expected_revision,
        ),
    )
    if updated.rowcount != 1:
        raise ValueError("方案已变化或不再等待回答，请重新读取")

    return get_fork_plan(connection, branch_id)