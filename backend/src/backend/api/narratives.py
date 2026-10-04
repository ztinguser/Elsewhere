from fastapi import APIRouter, HTTPException, Request

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.narratives import get_narrative, list_narratives, require_chapters
from backend.storage.simulation_tasks import get_latest_stage_task, queue_stage_task
from backend.storage.stages import get_stage, list_stages


router = APIRouter(prefix="/branches")


@router.get("/{branch_id}/chapters")
def read_chapters(branch_id: str, request: Request):
    with connect(request.app.state.life_db) as connection:
        if get_branch(connection, branch_id) is None:
            raise HTTPException(404, "分支不存在")
        return [item for item in list_narratives(connection, branch_id) if item["kind"] == "chapter"]


@router.get("/{branch_id}/chapters/{position}")
def read_chapter(branch_id: str, position: int, request: Request):
    for item in read_chapters(branch_id, request):
        if item["position"] == position:
            return item
    raise HTTPException(404, "已发布章节不存在")


@router.get("/{branch_id}/ending")
def read_ending(branch_id: str, request: Request):
    with connect(request.app.state.life_db) as connection:
        branch = get_branch(connection, branch_id)
        if branch is None:
            raise HTTPException(404, "分支不存在")
        stages = list_stages(connection, branch_id)
        reached = bool(stages and stages[-1]["end_reason"] == "target")
        contents = {item["kind"]: item for item in list_narratives(connection, branch_id)} if reached else {}
        today, retrospective = contents.get("today"), contents.get("retrospective")
        return {
            "target_date": branch["target_date"], "reached_target": reached,
            "status": "completed" if today and retrospective else "pending" if reached else "unavailable",
            "today": today, "retrospective": retrospective,
        }


@router.post("/{branch_id}/stages/{position}/narrative", status_code=202)
async def generate_missing_narrative(branch_id: str, position: int, request: Request):
    state = request.app.state
    try:
        with connect(state.life_db) as connection:
            stage = get_stage(connection, branch_id, position)
            if stage is None:
                raise HTTPException(404, "有效阶段不存在")
            require_chapters(connection, branch_id, position - 1)
            kinds = ("chapter", "today", "retrospective") if stage["end_reason"] == "target" else ("chapter",)
            latest = get_latest_stage_task(connection, branch_id, position)
            if all(get_narrative(connection, stage["id"], kind) for kind in kinds):
                return {"status": "completed", "task": latest}
            if latest and latest["status"] != "completed":
                return {"status": latest["status"], "task": latest}

        state.credentials.require_key()
        with connect(state.life_db) as connection:
            task = queue_stage_task(connection, branch_id, position=position)
            if task["input_data"].get("position") != position:
                raise ValueError("该分支存在其他未完成任务")
        state.worker.notify()
        return {"status": task["status"], "task": task}
    except ModelError as exc:
        return error_response(400 if exc.code == "MODEL_KEY_REQUIRED" else 502, exc.code, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
