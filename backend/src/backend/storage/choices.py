import json
import sqlite3
from datetime import UTC, datetime

from backend.models.decisions import DecisionInput, resolve_decision


def get_choice(
    connection: sqlite3.Connection,
    choice_id: str,
) -> dict | None:
    row = connection.execute(
        """
        SELECT choices.*, stages.branch_id, stages.position AS stage_position
        FROM simulation_choices AS choices
        JOIN simulation_stages AS stages ON stages.id = choices.stage_id
        WHERE choices.id = ?
        """,
        (choice_id,),
    ).fetchone()
    if row is None:
        return None

    choice = dict(row)
    choice["data"] = json.loads(choice["data"])
    if choice["decision_input"] is not None:
        choice["decision_input"] = json.loads(choice["decision_input"])
    return choice


def save_decision(
    connection: sqlite3.Connection,
    choice_id: str,
    data: DecisionInput,
) -> bool:
    choice = get_choice(connection, choice_id)
    if choice is None:
        raise ValueError("模拟选择节点不存在")

    if choice["decision"] is not None:
        if choice["decision_input"] != data.model_dump():
            raise ValueError("该节点已经作出决定，不能直接覆盖")
        return False

    decision = resolve_decision(choice["data"]["options"], data)
    if not decision.strip():
        raise ValueError("决定不能为空")

    updated = connection.execute(
        """
        UPDATE simulation_choices
        SET decision_input = ?, decision = ?, decided_at = ?
        WHERE id = ? AND decision IS NULL
        """,
        (
            data.model_dump_json(),
            decision,
            datetime.now(UTC).isoformat(),
            choice_id,
        ),
    )
    if updated.rowcount != 1:
        raise ValueError("节点状态已变化，请重新读取")
    return True