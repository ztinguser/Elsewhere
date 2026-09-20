from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.api.fork_plan_view import public_fork_plan
from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.llm.fork_plan import generate_fork_plan
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.fork_plans import get_fork_plan, save_initial_plan
from backend.storage.versions import get_fact_version


router = APIRouter(prefix="/branches")


@router.get("/{branch_id}/plan")
def read_fork_plan(branch_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        record = get_fork_plan(connection, branch_id)

    if record is None:
        raise HTTPException(404, "分叉方案不存在")

    return public_fork_plan(record)


@router.post("/{branch_id}/plan")
async def create_fork_plan(branch_id: str, request: Request):
    state = request.app.state

    with connect(state.life_db) as connection:
        record = get_fork_plan(connection, branch_id)
        if record is not None:
            return public_fork_plan(record)

        branch = get_branch(connection, branch_id)
        if branch is None:
            raise HTTPException(404, "分支不存在")

        snapshot = get_fact_version(
            connection, branch["fact_version_id"]
        )

    if branch_id in state.generating_plans:
        raise HTTPException(409, "方案正在生成，请稍后再试")

    state.generating_plans.add(branch_id)
    try:
        key = state.credentials.require_key()
        client = DeepSeekClient(key)
        try:
            result = await generate_fork_plan(client, branch, snapshot)
        finally:
            await client.aclose()

        with connect(state.life_db) as connection:
            record = save_initial_plan(connection, branch_id, result)

        return public_fork_plan(record)
    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))
    finally:
        state.generating_plans.discard(branch_id)