import json
import sqlite3


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