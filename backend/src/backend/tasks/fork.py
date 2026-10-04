from backend.llm.fork_plan import generate_fork_plan
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.fork_plans import get_fork_plan, save_answered_plan, save_initial_plan
from backend.storage.simulation_tasks import fail_stage_task
from backend.storage.task_queue import wait_for_input
from backend.storage.tasks import get_task, update_task_status
from backend.storage.versions import get_fact_version


def finish_plan_task(connection, task_id, record):
    if record["status"] == "blocked":
        fail_stage_task(connection, task_id, code="FORK_PLAN_BLOCKED",
                        message="方案存在前提冲突，请读取方案中的待修改内容")
    elif record["status"] == "confirmed":
        update_task_status(connection, task_id, expected_status="running",
                           status="completed", stage="completed")
    else:
        reason = "questionnaire" if record["status"] == "waiting_input" else "plan_confirmation"
        wait_for_input(connection, task_id, reason, record["branch_id"])


async def execute_fork_task(path, task, client):
    task_id, branch_id = task["id"], task["branch_id"]
    data = task["input_data"]
    with connect(path) as connection:
        if not update_task_status(connection, task_id, expected_status="queued",
                                  status="running", stage=data["operation"]):
            return
        branch = get_branch(connection, branch_id)
        snapshot = get_fact_version(connection, branch["fact_version_id"])
        record = get_fork_plan(connection, branch_id)
        if data["operation"] == "fork_plan" and record:
            finish_plan_task(connection, task_id, record)
            return

    if data["operation"] == "fork_answers":
        result = await generate_fork_plan(client, branch, snapshot,
                                         initial_plan=record["initial_result"]["plan"],
                                         answers=data["answers"])
    else:
        result = await generate_fork_plan(client, branch, snapshot)

    with connect(path) as connection:
        if get_task(connection, task_id)["status"] != "running":
            return
        if data["operation"] == "fork_answers":
            record = save_answered_plan(connection, branch_id, answers=data["answers"],
                                       result=result, expected_revision=data["request"]["expected_revision"])
        else:
            record = save_initial_plan(connection, branch_id, result)
        finish_plan_task(connection, task_id, record)
