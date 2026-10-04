import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.storage.tasks import create_task, get_task


def latest_operation(connection: sqlite3.Connection, branch_id: str, operation: str):
    row = connection.execute(
        """SELECT id FROM tasks WHERE branch_id = ?
           AND json_extract(input_data, '$.operation') = ?
           ORDER BY created_at DESC, rowid DESC LIMIT 1""",
        (branch_id, operation),
    ).fetchone()
    return get_task(connection, row["id"]) if row else None


def enqueue(connection: sqlite3.Connection, branch_id: str, input_data: dict) -> dict:
    active = connection.execute(
        """SELECT id FROM tasks WHERE branch_id = ?
           AND status IN ('queued', 'running', 'waiting_input', 'interrupted')""",
        (branch_id,),
    ).fetchone()
    if active:
        raise ValueError("该分支存在未完成任务，请先处理当前任务")
    task_id = create_task(connection, task_id=uuid4().hex, kind="generate_branch",
                          branch_id=branch_id, input_data=input_data)
    return get_task(connection, task_id)


def finish_wait(connection: sqlite3.Connection, branch_id: str, reason: str, object_id: str):
    connection.execute(
        """UPDATE tasks SET status = 'completed', stage = 'completed',
           waiting_reason = NULL, waiting_object_id = NULL, updated_at = ?
           WHERE branch_id = ? AND status = 'waiting_input'
           AND waiting_reason = ? AND waiting_object_id = ?""",
        (datetime.now(UTC).isoformat(), branch_id, reason, object_id),
    )


def wait_for_input(connection: sqlite3.Connection, task_id: str, reason: str, object_id: str):
    connection.execute(
        """UPDATE tasks SET status = 'waiting_input', stage = 'waiting_input',
           waiting_reason = ?, waiting_object_id = ?, updated_at = ?
           WHERE id = ? AND status IN ('queued', 'running')""",
        (reason, object_id, datetime.now(UTC).isoformat(), task_id),
    )


def interrupt_pending(connection: sqlite3.Connection):
    connection.execute(
        """UPDATE tasks SET status = 'interrupted', updated_at = ?
           WHERE status IN ('queued', 'running')""",
        (datetime.now(UTC).isoformat(),),
    )
