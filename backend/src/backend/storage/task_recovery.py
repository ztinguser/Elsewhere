from datetime import UTC, datetime

from backend.storage.fork_plans import get_fork_plan
from backend.storage.narratives import get_narrative
from backend.storage.stages import get_stage_detail
from backend.storage.tasks import WORKFLOW_VERSION


def require_workflow_version(task):
    if task["workflow_version"] != WORKFLOW_VERSION:
        raise ValueError("任务工作流版本不兼容，请使用对应版本的程序")


def saved_outcome(connection, task):
    """正式结果是恢复依据；检查点落后于发布事务时也不重跑模型。"""
    data, branch_id = task["input_data"], task["branch_id"]
    if data.get("operation") in ("fork_plan", "fork_answers"):
        plan = get_fork_plan(connection, branch_id)
        if not plan:
            return None
        if data["operation"] == "fork_answers" and plan["answers"] != data["answers"]:
            return None
        if plan["status"] == "blocked":
            return "failed", None, None
        if plan["status"] == "confirmed":
            return "completed", None, None
        reason = "questionnaire" if plan["status"] == "waiting_input" else "plan_confirmation"
        return "waiting_input", reason, branch_id
    if "position" in data:
        stage = get_stage_detail(connection, branch_id, data["position"])
        if not stage:
            return None
        kinds = ("chapter", "today", "retrospective") if stage["end_reason"] == "target" else ("chapter",)
        if not all(get_narrative(connection, stage["id"], kind) for kind in kinds):
            return None
        choice = stage["choice"]
        if choice and choice["decision"] is None:
            return "waiting_input", "simulation_choice", choice["id"]
        return "completed", None, None
    return None


def reconcile_task(connection, task):
    outcome = saved_outcome(connection, task)
    if not outcome:
        return False
    status, reason, object_id = outcome
    if (task["status"], task["waiting_reason"], task["waiting_object_id"]) == outcome:
        return True
    blocked = status == "failed"
    connection.execute(
        """UPDATE tasks SET status = ?, stage = ?, waiting_reason = ?, waiting_object_id = ?,
           error_code = ?, error_message = ?, updated_at = ? WHERE id = ?""",
        (status, status, reason, object_id,
         "FORK_PLAN_BLOCKED" if blocked else None,
         "方案存在前提冲突，请读取方案中的待修改内容" if blocked else None,
         datetime.now(UTC).isoformat(), task["id"]),
    )
    return True
