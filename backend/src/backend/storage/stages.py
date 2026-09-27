import json
import sqlite3

from backend.storage.choices import get_choice


def get_stage(
    connection: sqlite3.Connection,
    branch_id: str,
    position: int,
) -> dict | None:
    row = connection.execute(
        """
        SELECT * FROM simulation_stages
        WHERE branch_id = ? AND position = ?
        """,
        (branch_id, position),
    ).fetchone()
    if row is None:
        return None

    stage = dict(row)
    stage["review"] = json.loads(stage["review"])
    return stage


def list_stages(
    connection: sqlite3.Connection,
    branch_id: str,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT * FROM simulation_stages
        WHERE branch_id = ?
        ORDER BY position
        """,
        (branch_id,),
    ).fetchall()

    stages = [dict(row) for row in rows]
    for stage in stages:
        stage["review"] = json.loads(stage["review"])
    return stages


def get_stage_detail(
    connection: sqlite3.Connection,
    branch_id: str,
    position: int,
) -> dict | None:
    stage = get_stage(connection, branch_id, position)
    if stage is None:
        return None

    rows = connection.execute(
        """
        SELECT * FROM events
        WHERE branch_id = ? AND stage_id = ? AND status = 'validated'
        ORDER BY position
        """,
        (branch_id, stage["id"]),
    ).fetchall()
    stage["events"] = [
        {**dict(row), "data": json.loads(row["data"])}
        for row in rows
    ]

    row = connection.execute(
        "SELECT id FROM simulation_choices WHERE stage_id = ?",
        (stage["id"],),
    ).fetchone()
    stage["choice"] = get_choice(connection, row["id"]) if row is not None else None
    return stage