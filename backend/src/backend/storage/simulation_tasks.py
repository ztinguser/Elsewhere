import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.storage.simulation_context import build_simulation_context
from backend.storage.tasks import create_task, get_task


def queue_stage_task(
    connection: sqlite3.Connection,
    branch_id: str,
) -> dict:
    row = connection.execute(
        """
        SELECT id FROM tasks
        WHERE branch_id = ?
          AND status IN ('queued', 'running', 'waiting_input', 'interrupted')
        """,
        (branch_id,),
    ).fetchone()
    if row is not None:
        return get_task(connection, row["id"])

    context = build_simulation_context(connection, branch_id)
    task_id = create_task(
        connection,
        task_id=uuid4().hex,
        kind="generate_branch",
        branch_id=branch_id,
        input_data={"position": context["next_position"]},
    )
    return get_task(connection, task_id)


def fail_stage_task(
    connection: sqlite3.Connection,
    task_id: str,
    *,
    code: str,
    message: str,
    expected_status: str = "running",
) -> bool:
    result = connection.execute(
        """
        UPDATE tasks
        SET status = 'failed', error_code = ?, error_message = ?, updated_at = ?
        WHERE id = ? AND status = ?
        """,
        (code, message, datetime.now(UTC).isoformat(), task_id, expected_status),
    )
    return result.rowcount == 1


def get_latest_stage_task(
    connection: sqlite3.Connection,
    branch_id: str,
    position: int,
) -> dict | None:
    row = connection.execute(
        """
        SELECT id FROM tasks
        WHERE branch_id = ? AND kind = 'generate_branch'
          AND json_extract(input_data, '$.position') = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT 1
        """,
        (branch_id, position),
    ).fetchone()
    return get_task(connection, row["id"]) if row is not None else None