import json
from datetime import UTC, datetime
from uuid import uuid4

from backend.models.branch_rewrites import BranchRewriteInput
from backend.models.decisions import resolve_decision
from backend.storage.branch_prefix import copy_prefix
from backend.storage.choices import get_choice
from backend.storage.narratives import require_chapters
from backend.storage.simulation_tasks import get_latest_stage_task, queue_stage_task


def rewrite_branch(connection, branch_id: str, choice_id: str, data: BranchRewriteInput) -> dict:
    # 先写入请求占位，串行化重复请求；整个分支与任务在同一事务提交。
    payload = {"branch_id": branch_id, "choice_id": choice_id, "decision": data.decision.model_dump()}
    connection.execute(
        "INSERT INTO fork_requests (request_id, input_data) VALUES (?, ?) ON CONFLICT DO NOTHING",
        (data.request_id, json.dumps(payload, ensure_ascii=False)),
    )
    saved = connection.execute(
        "SELECT * FROM fork_requests WHERE request_id = ?", (data.request_id,),
    ).fetchone()
    if json.loads(saved["input_data"]) != payload:
        raise ValueError("同一请求编号不能用于不同的创建参数")
    choice = get_choice(connection, choice_id)
    if choice is None or choice["branch_id"] != branch_id:
        raise ValueError("该分支下的选择节点不存在")
    position = choice["stage_position"]
    if saved["branch_id"]:
        return {"id": saved["branch_id"], "task": get_latest_stage_task(connection, saved["branch_id"], position + 1)}
    if choice["decision"] is None:
        raise ValueError("尚未决定的节点请直接提交决定")
    decision = resolve_decision(choice["data"]["options"], data.decision)
    if decision == choice["decision"]:
        raise ValueError("请选择与原决定不同的决定")
    require_chapters(connection, branch_id, position)

    child_id = uuid4().hex
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """INSERT INTO branches
           (id, parent_id, fact_version_id, fork_fact_id, alternative, target_date,
            assumptions, status, created_at, updated_at, fork_choice_id)
           SELECT ?, id, fact_version_id, fork_fact_id, alternative, target_date,
                  assumptions, 'ready', ?, ?, ? FROM branches WHERE id = ?""",
        (child_id, now, now, choice_id, branch_id),
    )
    connection.execute(
        """INSERT INTO fork_plans
           (branch_id, initial_result, final_result, answers, status, revision, created_at, updated_at)
           SELECT ?, initial_result, final_result, answers, status, revision, created_at, updated_at
           FROM fork_plans WHERE branch_id = ? AND status = 'confirmed'""",
        (child_id, branch_id),
    )
    child_choice_id = copy_prefix(connection, branch_id, child_id, position)
    connection.execute(
        "UPDATE simulation_choices SET decision_input = ?, decision = ?, decided_at = ? WHERE id = ?",
        (data.decision.model_dump_json(), decision, now, child_choice_id),
    )
    task = queue_stage_task(connection, child_id)
    connection.execute(
        "UPDATE fork_requests SET branch_id = ? WHERE request_id = ?", (child_id, data.request_id),
    )
    return {"id": child_id, "task": task}
