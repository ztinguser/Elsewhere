import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.storage.versions import get_fact_version


def create_branch(
    connection: sqlite3.Connection,
    *,
    fact_version_id: str,
    fork_fact_id: str,
    alternative: str,
    target_date: str,
) -> str:
    snapshot = get_fact_version(connection, fact_version_id)
    if snapshot is None:
        raise ValueError("事实版本不存在")

    if not any(fact["id"] == fork_fact_id for fact in snapshot["facts"]):
        raise ValueError("分叉节点不属于该事实版本")

    branch_id = uuid4().hex
    now = datetime.now(UTC).isoformat()

    connection.execute(
        """
        INSERT INTO branches (
            id, fact_version_id, fork_fact_id, alternative,
            target_date, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            branch_id,
            fact_version_id,
            fork_fact_id,
            alternative,
            target_date,
            now,
            now,
        ),
    )
    return branch_id


def get_branch(
    connection: sqlite3.Connection, branch_id: str
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM branches WHERE id = ?",
        (branch_id,),
    ).fetchone()

    if row is None:
        return None

    branch = dict(row)
    branch["assumptions"] = json.loads(branch["assumptions"])
    return branch