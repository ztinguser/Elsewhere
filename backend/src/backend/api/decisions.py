from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.models.decisions import DecisionInput
from backend.simulation.execution import execute_stage_task
from backend.storage.choices import get_choice, save_decision
from backend.storage.database import connect
from backend.storage.simulation_tasks import (
    fail_stage_task, get_latest_stage_task, queue_stage_task,
)


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/choices/{choice_id}/decision")
async def submit_decision(
    branch_id: str,
    choice_id: str,
    data: DecisionInput,
    request: Request,
):
    state = request.app.state

    try:
        with connect(state.life_db) as connection:
            choice = get_choice(connection, choice_id)
            if choice is None or choice["branch_id"] != branch_id:
                raise HTTPException(404, "该分支下的选择节点不存在")
            position = choice["stage_position"] + 1
            if not save_decision(connection, choice_id, data):
                return {
                    "choice": choice,
                    "task": get_latest_stage_task(connection, branch_id, position),
                }

            task = queue_stage_task(connection, branch_id)
            if task["input_data"].get("position") != position:
                raise ValueError("当前任务与选择节点对应的阶段不一致")
            choice = get_choice(connection, choice_id)

        try:
            key = state.credentials.require_key()
            client = DeepSeekClient(key)
        except Exception as exc:
            code = exc.code if isinstance(exc, ModelError) else "MODEL_SETUP_FAILED"
            message = str(exc) if isinstance(exc, ModelError) else "模型客户端初始化失败，请重试"
            with connect(state.life_db) as connection:
                fail_stage_task(
                    connection, task["id"], code=code, message=message,
                    expected_status="queued",
                )
            raise ModelError(code, message) from None

        try:
            task = await execute_stage_task(state.life_db, task["id"], client)
        finally:
            await client.aclose()

        return {"choice": choice, "task": task}

    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None