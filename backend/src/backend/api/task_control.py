from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.api.simulation_read import read_task
from backend.llm.client import ModelError
from backend.storage.database import connect
from backend.storage.task_recovery import reconcile_task
from backend.storage.tasks import get_task


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/tasks/{task_id}/cancel")
async def cancel_task(branch_id: str, task_id: str, request: Request):
    state = request.app.state
    read_task(branch_id, task_id, request)
    with connect(state.life_db) as connection:
        task = get_task(connection, task_id)
        if task["status"] in ("completed", "failed"):
            raise HTTPException(409, "任务已经结束，不能取消")
        if task["status"] != "cancelled":
            connection.execute("UPDATE tasks SET status = 'cancelled', updated_at = ? WHERE id = ?",
                               (datetime.now(UTC).isoformat(), task_id))
        task = get_task(connection, task_id)
    state.worker.cancel(task_id)
    return task


@router.post("/{branch_id}/tasks/{task_id}/resume", status_code=202)
async def resume_task(branch_id: str, task_id: str, request: Request):
    state = request.app.state
    task = read_task(branch_id, task_id, request)
    try:
        await state.worker.require_version(task)
        with connect(state.life_db) as connection:
            task = get_task(connection, task_id)
            if task["status"] in ("queued", "running", "waiting_input", "completed"):
                return task
            if task["status"] not in ("interrupted", "cancelled"):
                raise ValueError("失败任务请使用重试接口")
            latest = connection.execute(
                "SELECT id FROM tasks WHERE branch_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (branch_id,),
            ).fetchone()
            if latest["id"] != task_id:
                raise ValueError("该分支已有后续任务，请使用最新任务")
            if not reconcile_task(connection, task):
                state.credentials.require_key()
                connection.execute(
                    """UPDATE tasks SET status = 'queued', execution_id = ?, waiting_reason = NULL,
                       waiting_object_id = NULL, error_code = NULL, error_message = NULL,
                       updated_at = ? WHERE id = ?""",
                    (uuid4().hex, datetime.now(UTC).isoformat(), task_id),
                )
            task = get_task(connection, task_id)
        state.worker.notify()
        return task
    except ModelError as exc:
        return error_response(400, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
