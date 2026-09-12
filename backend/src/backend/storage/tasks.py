import json
import sqlite3
from datetime import UTC, datetime


def create_task(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    kind: str,
    input_data: dict,
    branch_id: str | None = None,
) -> str:
    existing = get_task(connection, task_id)
    if existing is not None:
        if (
            existing["kind"] != kind
            or existing["branch_id"] != branch_id
            or existing["input_data"] != input_data
        ):
            raise ValueError("同一任务标识不能用于不同请求")
        return task_id

    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO tasks (
            id, kind, branch_id, input_data, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            kind,
            branch_id,
            json.dumps(input_data, ensure_ascii=False),
            now,
            now,
        ),
    )
    return task_id


def get_task(
    connection: sqlite3.Connection, task_id: str
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None

    task = dict(row)
    task["input_data"] = json.loads(task["input_data"])
    return task


def update_task_status(
    connection: sqlite3.Connection,
    task_id: str,
    *,
    expected_status: str,
    status: str,
    stage: str,
) -> bool:
    result = connection.execute(
        """
        UPDATE tasks
        SET status = ?, stage = ?, updated_at = ?
        WHERE id = ? AND status = ?
        """,
        (
            status,
            stage,
            datetime.now(UTC).isoformat(),
            task_id,
            expected_status,
        ),
    )
    return result.rowcount == 1