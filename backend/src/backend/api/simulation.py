from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.simulation_tasks import get_latest_stage_task, queue_stage_task
from backend.storage.stages import get_stage


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/start", status_code=202)
async def start_simulation(branch_id: str, request: Request):
    state = request.app.state

    try:
        with connect(state.life_db) as connection:
            if get_branch(connection, branch_id) is None:
                raise HTTPException(404, "分支不存在")
            task = get_latest_stage_task(connection, branch_id, 1)
            if task is not None:
                return task
            if get_stage(connection, branch_id, 1) is not None:
                raise HTTPException(409, "首阶段已经存在，请读取已有结果")

        state.credentials.require_key()
        with connect(state.life_db) as connection:
            task = queue_stage_task(connection, branch_id)
            if task["input_data"].get("position") != 1:
                raise ValueError("启动接口只能生成首阶段")
        state.worker.notify()
        return task

    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None