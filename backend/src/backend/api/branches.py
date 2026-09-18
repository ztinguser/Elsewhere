from fastapi import APIRouter, HTTPException, Request

from backend.models.forks import ForkInput
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.forks import create_fork
from backend.storage.versions import get_fact_version


router = APIRouter(prefix="/branches")


@router.post("", status_code=201)
def add_branch(data: ForkInput, request: Request) -> dict:
    try:
        with connect(request.app.state.life_db) as connection:
            branch_id = create_fork(
                connection,
                request_id=data.request_id,
                memory_id=data.memory_id,
                alternative=data.alternative,
                expected_revision=data.expected_revision,
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return {"id": branch_id}


@router.get("/{branch_id}")
def read_branch(branch_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        branch = get_branch(connection, branch_id)
        if branch is None:
            raise HTTPException(404, "分支不存在")

        branch["snapshot"] = get_fact_version(
            connection, branch["fact_version_id"]
        )

    return branch