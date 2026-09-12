import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.events import EventData


def create_event(
    connection: sqlite3.Connection,
    *,
    branch_id: str,
    position: int,
    data: EventData,
) -> str:
    row = connection.execute(
        """
        SELECT fact_versions.snapshot
        FROM branches
        JOIN fact_versions ON fact_versions.id = branches.fact_version_id
        WHERE branches.id = ?
        """,
        (branch_id,),
    ).fetchone()

    if row is None:
        raise ValueError("分支不存在")

    snapshot = json.loads(row["snapshot"])
    fact_ids = {fact["id"] for fact in snapshot["facts"]}
    if not set(data.fact_ids) <= fact_ids:
        raise ValueError("事件引用了分支事实版本之外的节点")

    event_id = uuid4().hex
    connection.execute(
        """
        INSERT INTO events (id, branch_id, position, data, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            event_id,
            branch_id,
            position,
            data.model_dump_json(),
            datetime.now(UTC).isoformat(),
        ),
    )
    return event_id


def list_events(
    connection: sqlite3.Connection, branch_id: str
) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM events WHERE branch_id = ? ORDER BY position",
        (branch_id,),
    ).fetchall()

    events = []
    for row in rows:
        event = dict(row)
        event["data"] = json.loads(event["data"])
        events.append(event)
    return events