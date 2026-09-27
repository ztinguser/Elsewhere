from fastapi import APIRouter, HTTPException, Request

from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.stages import get_stage_detail, list_stages
from backend.storage.tasks import get_task


router = APIRouter(prefix="/branches")


@router.get("/{branch_id}/tasks/{task_id}")
def read_task(branch_id: str, task_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        task = get_task(connection, task_id)
    if task is None or task["branch_id"] != branch_id:
        raise HTTPException(404, "该分支下的任务不存在")
    return task


@router.get("/{branch_id}/stages")
def read_stages(branch_id: str, request: Request) -> list[dict]:
    with connect(request.app.state.life_db) as connection:
        if get_branch(connection, branch_id) is None:
            raise HTTPException(404, "分支不存在")
        return list_stages(connection, branch_id)


@router.get("/{branch_id}/stages/{position}")
def read_stage(branch_id: str, position: int, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        stage = get_stage_detail(connection, branch_id, position)
    if stage is None:
        raise HTTPException(404, "阶段不存在")
    return stage