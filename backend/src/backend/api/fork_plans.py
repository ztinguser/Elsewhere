from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.api.fork_plan_view import public_fork_plan
from backend.llm.client import ModelError
from backend.models.fork_plan import ForkPlanConfirm
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.fork_confirmation import confirm_fork_plan
from backend.storage.fork_plans import get_fork_plan
from backend.storage.task_queue import enqueue, finish_wait, latest_operation
from backend.storage.tasks import get_task, update_task_status
from backend.tasks.fork import finish_plan_task


router = APIRouter(prefix="/branches")


@router.get("/{branch_id}/plan")
def read_fork_plan(branch_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        record = get_fork_plan(connection, branch_id)
    if record is None:
        raise HTTPException(404, "分叉方案不存在")
    return public_fork_plan(record)


@router.post("/{branch_id}/plan", status_code=202)
async def create_fork_plan(branch_id: str, request: Request):
    state = request.app.state
    try:
        with connect(state.life_db) as connection:
            if get_branch(connection, branch_id) is None:
                raise HTTPException(404, "分支不存在")
            task = latest_operation(connection, branch_id, "fork_plan")
            if task:
                return task
            record = get_fork_plan(connection, branch_id)
            if record is None:
                state.credentials.require_key()
            task = enqueue(connection, branch_id, {"operation": "fork_plan"})
            if record:
                update_task_status(connection, task["id"], expected_status="queued",
                                   status="running", stage="fork_plan")
                finish_plan_task(connection, task["id"], record)
                return get_task(connection, task["id"])
        state.worker.notify()
        return task
    except ModelError as exc:
        return error_response(400, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@router.post("/{branch_id}/plan/confirm")
async def confirm_plan(branch_id: str, data: ForkPlanConfirm, request: Request) -> dict:
    try:
        with connect(request.app.state.life_db) as connection:
            record = confirm_fork_plan(connection, branch_id, expected_revision=data.expected_revision)
            finish_wait(connection, branch_id, "plan_confirmation", branch_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    request.app.state.worker.notify()
    return public_fork_plan(record)
