from fastapi import APIRouter, HTTPException, Request

from backend.models.branch_rewrites import BranchRewriteInput
from backend.storage.branch_rewrites import rewrite_branch
from backend.storage.database import connect


router = APIRouter(prefix="/branches")


@router.post("/{branch_id}/choices/{choice_id}/fork", status_code=202)
async def fork_choice(branch_id: str, choice_id: str, data: BranchRewriteInput, request: Request):
    try:
        with connect(request.app.state.life_db) as connection:
            result = rewrite_branch(connection, branch_id, choice_id, data)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    request.app.state.worker.notify()
    return result
