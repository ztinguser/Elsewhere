import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.facts import FactData


def create_fragment(
    connection: sqlite3.Connection, content: str
) -> str:
    fragment_id = uuid4().hex
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO fragments (id, content, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (fragment_id, content, now, now),
    )
    return fragment_id


def list_fragments(connection: sqlite3.Connection) -> list[dict]:
    return [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM fragments ORDER BY created_at, id"
        )
    ]


def create_fact(
    connection: sqlite3.Connection,
    *,
    data: FactData,
    fragment_ids: list[str],
) -> str:
    if not fragment_ids:
        raise ValueError("事实节点必须关联原文来源")

    fact_id = uuid4().hex
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO fact_nodes (
            id, content, kind, time_text, occurred_from,
            occurred_to, uncertainty, created_at, updated_at
        )
        VALUES (
            :id, :content, :kind, :time_text, :occurred_from,
            :occurred_to, :uncertainty, :now, :now
        )
        """,
        {**data.model_dump(), "id": fact_id, "now": now},
    )
    connection.executemany(
        "INSERT INTO fact_sources (fact_id, fragment_id) VALUES (?, ?)",
        [(fact_id, fragment_id) for fragment_id in fragment_ids],
    )
    return fact_id


def get_fact(
    connection: sqlite3.Connection, fact_id: str
) -> dict | None:
    row = connection.execute(
        "SELECT * FROM fact_nodes WHERE id = ?",
        (fact_id,),
    ).fetchone()
    if row is None:
        return None

    fact = dict(row)
    fact["sources"] = [
        dict(row)
        for row in connection.execute(
            """
            SELECT fragments.*
            FROM fragments
            JOIN fact_sources ON fact_sources.fragment_id = fragments.id
            WHERE fact_sources.fact_id = ?
            ORDER BY fragments.created_at, fragments.id
            """,
            (fact_id,),
        )
    ]
    return fact