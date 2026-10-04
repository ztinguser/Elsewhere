from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.models.fork_answers import ForkAnswersInput, prepare_fork_answers
from backend.storage.database import connect
from backend.storage.fork_plans import get_fork_plan
from backend.storage.task_queue import enqueue, finish_wait, latest_operation


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/plan/answers", status_code=202)
async def submit_fork_answers(branch_id: str, data: ForkAnswersInput, request: Request):
    state = request.app.state
    try:
        with connect(state.life_db) as connection:
            record = get_fork_plan(connection, branch_id)
            if record is None:
                raise HTTPException(404, "分叉方案不存在")
            previous = latest_operation(connection, branch_id, "fork_answers")
            if previous:
                if previous["input_data"]["request"] == data.model_dump():
                    return previous
                raise ValueError("问卷答案已经提交，请先处理已有任务")
            answers = prepare_fork_answers(record, data)
            state.credentials.require_key()
            finish_wait(connection, branch_id, "questionnaire", branch_id)
            task = enqueue(connection, branch_id, {
                "operation": "fork_answers", "request": data.model_dump(), "answers": answers,
            })
        state.worker.notify()
        return task
    except ModelError as exc:
        return error_response(400, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
