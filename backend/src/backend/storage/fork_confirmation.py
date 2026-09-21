import json
import sqlite3
from datetime import UTC, datetime

from backend.storage.fork_plans import get_fork_plan


def confirm_fork_plan(
    connection: sqlite3.Connection,
    branch_id: str,
    *,
    expected_revision: int,
) -> dict:
    now = datetime.now(UTC).isoformat()
    updated = connection.execute(
        """
        UPDATE fork_plans
        SET status = 'confirmed', revision = revision + 1,
            updated_at = ?
        WHERE branch_id = ? AND revision = ?
            AND status = 'waiting_confirmation'
        """,
        (now, branch_id, expected_revision),
    )
    if updated.rowcount != 1:
        raise ValueError("方案已变化或当前不能确认，请重新读取")

    record = get_fork_plan(connection, branch_id)
    result = record["final_result"] or record["initial_result"]
    updated = connection.execute(
        """
        UPDATE branches
        SET status = 'ready', assumptions = ?, updated_at = ?
        WHERE id = ? AND status = 'draft'
        """,
        (
            json.dumps(result["plan"]["assumptions"], ensure_ascii=False),
            now,
            branch_id,
        ),
    )
    if updated.rowcount != 1:
        raise ValueError("分支状态已变化，不能确认方案")

    return record