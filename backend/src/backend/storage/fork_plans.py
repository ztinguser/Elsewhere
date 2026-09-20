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