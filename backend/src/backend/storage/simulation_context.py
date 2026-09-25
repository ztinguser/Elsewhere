import json
import sqlite3

from backend.storage.branches import get_branch
from backend.storage.fork_plans import get_fork_plan
from backend.storage.versions import get_fact_version


def build_simulation_context(
    connection: sqlite3.Connection,
    branch_id: str,
) -> dict:
    branch = get_branch(connection, branch_id)
    if branch is None or branch["status"] != "ready":
        raise ValueError("分支不存在或当前不能继续推演")

    record = get_fork_plan(connection, branch_id)
    if record is None or record["status"] != "confirmed":
        raise ValueError("请先确认分叉方案")
    plan = (record["final_result"] or record["initial_result"])["plan"]

    rows = connection.execute(
        """
        SELECT stages.position, stages.end_time_text, stages.end_reason,
               stages.id, choices.data AS choice_data, choices.decision
        FROM simulation_stages AS stages
        LEFT JOIN simulation_choices AS choices ON choices.stage_id = stages.id
        WHERE stages.branch_id = ?
        ORDER BY stages.position
        """,
        (branch_id,),
    ).fetchall()

    history = []
    for row in rows:
        if row["end_reason"] == "target":
            raise ValueError("已经抵达终点，不能继续推进")
        if not (row["decision"] or "").strip():
            raise ValueError("请先提交上一阶段的决定")

        events = connection.execute(
            """
            SELECT data FROM events
            WHERE stage_id = ? AND branch_id = ? AND status = 'validated'
            ORDER BY position
            """,
            (row["id"], branch_id),
        ).fetchall()
        history.append({
            "position": row["position"],
            "end_time_text": row["end_time_text"],
            "events": [json.loads(event["data"]) for event in events],
            "decision": {
                "situation": json.loads(row["choice_data"])["situation"],
                "text": row["decision"],
            },
        })

    fact_ids = {branch["fork_fact_id"]}
    for field in ("preserved", "affected", "external_conditions", "information_limits"):
        fact_ids.update(item["fact_id"] for item in plan[field])
    for stage in history:
        for event in stage["events"]:
            fact_ids.update(event["fact_ids"])

    snapshot = get_fact_version(connection, branch["fact_version_id"])
    facts = [
        {"id": fact["id"], "time_text": fact.get("time_text"), "content": fact["content"]}
        for fact in snapshot["facts"]
        if fact["id"] in fact_ids
    ]
    return {
        "fork_fact_id": branch["fork_fact_id"],
        "alternative": branch["alternative"],
        "target_date": branch["target_date"],
        "next_position": rows[-1]["position"] + 1 if rows else 1,
        "plan": {
            key: value for key, value in plan.items()
            if key not in ("questions", "blockers")
        },
        "facts": facts,
        "history": history,
    }