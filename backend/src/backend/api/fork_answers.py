from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.api.fork_plan_view import public_fork_plan
from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.llm.fork_plan import generate_fork_plan
from backend.models.fork_answers import ForkAnswersInput, prepare_fork_answers
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.fork_plans import get_fork_plan, save_answered_plan
from backend.storage.versions import get_fact_version


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/plan/answers")
async def submit_fork_answers(
    branch_id: str,
    data: ForkAnswersInput,
    request: Request,
):
    state = request.app.state

    try:
        with connect(state.life_db) as connection:
            record = get_fork_plan(connection, branch_id)
            if record is None:
                raise HTTPException(404, "分叉方案不存在")

            answers = prepare_fork_answers(record, data)
            branch = get_branch(connection, branch_id)
            snapshot = get_fact_version(
                connection, branch["fact_version_id"]
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    if branch_id in state.generating_plans:
        raise HTTPException(409, "方案正在生成，请稍后再试")

    state.generating_plans.add(branch_id)
    try:
        key = state.credentials.require_key()
        client = DeepSeekClient(key)
        try:
            result = await generate_fork_plan(
                client,
                branch,
                snapshot,
                initial_plan=record["initial_result"]["plan"],
                answers=answers,
            )
        finally:
            await client.aclose()

        with connect(state.life_db) as connection:
            record = save_answered_plan(
                connection,
                branch_id,
                answers=answers,
                result=result,
                expected_revision=data.expected_revision,
            )

        return public_fork_plan(record)
    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    finally:
        state.generating_plans.discard(branch_id)