from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.simulation.execution import execute_stage_task
from backend.storage.database import connect
from backend.storage.simulation_tasks import get_latest_stage_task, queue_stage_task
from backend.storage.tasks import get_task


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/tasks/{task_id}/retry")
async def retry_stage(branch_id: str, task_id: str, request: Request):
    state = request.app.state

    try:
        with connect(state.life_db) as connection:
            old = get_task(connection, task_id)
            if (
                old is None
                or old["branch_id"] != branch_id
                or "position" not in old["input_data"]
            ):
                raise HTTPException(404, "该分支下的阶段任务不存在")
            if old["status"] != "failed":
                raise HTTPException(409, "只有失败任务可以重试")

            position = old["input_data"]["position"]
            latest = get_latest_stage_task(connection, branch_id, position)
            if latest["id"] != task_id:
                return latest

        key = state.credentials.require_key()
        client = DeepSeekClient(key)
        try:
            with connect(state.life_db) as connection:
                latest = get_latest_stage_task(connection, branch_id, position)
                if latest["id"] != task_id:
                    return latest
                task = queue_stage_task(connection, branch_id, position=position)
                if task["input_data"].get("position") != position:
                    raise ValueError("当前进度与待重试阶段不一致")

            return await execute_stage_task(state.life_db, task["id"], client)
        finally:
            await client.aclose()

    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
