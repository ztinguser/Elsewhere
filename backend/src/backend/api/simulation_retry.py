from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.storage.database import connect
from backend.storage.simulation_tasks import get_latest_stage_task, queue_stage_task
from backend.storage.task_queue import enqueue
from backend.storage.tasks import get_task


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/tasks/{task_id}/retry", status_code=202)
async def retry_stage(branch_id: str, task_id: str, request: Request):
    state = request.app.state
    try:
        with connect(state.life_db) as connection:
            old = get_task(connection, task_id)
            if old is None or old["branch_id"] != branch_id:
                raise HTTPException(404, "该分支下的任务不存在")
            if old["status"] != "failed":
                raise HTTPException(409, "只有失败任务可以重试")
            if old["error_code"] == "FORK_PLAN_BLOCKED":
                raise HTTPException(409, "方案存在前提冲突，请修改前提后创建新分支")
            row = connection.execute("SELECT id FROM tasks WHERE retry_of = ?", (task_id,)).fetchone()
            if row:
                return get_task(connection, row["id"])
            if "position" in old["input_data"]:
                position = old["input_data"]["position"]
                latest = get_latest_stage_task(connection, branch_id, position)
                if latest["id"] != task_id:
                    return latest
            state.credentials.require_key()
            if "position" in old["input_data"]:
                task = queue_stage_task(connection, branch_id, position=position)
                if task["input_data"].get("position") != position:
                    raise ValueError("该分支存在其他未完成任务")
            else:
                task = enqueue(connection, branch_id, old["input_data"])
            connection.execute("UPDATE tasks SET retry_of = ?, retry_count = ? WHERE id = ?",
                               (task_id, old["retry_count"] + 1, task["id"]))
            task = get_task(connection, task["id"])
        state.worker.notify()
        return task
    except ModelError as exc:
        return error_response(400, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
