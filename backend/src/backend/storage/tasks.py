import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4


WORKFLOW_VERSION = "2"


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
            id, kind, branch_id, input_data, created_at, updated_at,
            workflow_version, execution_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            kind,
            branch_id,
            json.dumps(input_data, ensure_ascii=False),
            now,
            now,
            WORKFLOW_VERSION,
            uuid4().hex,
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
    execution_id: str | None = None,
) -> bool:
    result = connection.execute(
        """
        UPDATE tasks
        SET status = ?, stage = ?, updated_at = ?
        WHERE id = ? AND status = ?
          AND (? IS NULL OR execution_id = ?)
        """,
        (
            status,
            stage,
            datetime.now(UTC).isoformat(),
            task_id,
            expected_status,
            execution_id,
            execution_id,
        ),
    )
    return result.rowcount == 1


def is_running(connection: sqlite3.Connection, task: dict) -> bool:
    current = get_task(connection, task["id"])
    return bool(current and current["status"] == "running"
                and current["execution_id"] == task["execution_id"])
