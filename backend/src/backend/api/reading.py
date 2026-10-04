from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.reading import get_reading_position, save_reading_position


router = APIRouter(prefix="/branches")


class ReadingPositionInput(BaseModel):
    paragraph_id: str
    char_offset: int = Field(default=0, ge=0, strict=True)


@router.get("/{branch_id}/reading-position")
def read_position(branch_id: str, request: Request):
    with connect(request.app.state.life_db) as connection:
        if get_branch(connection, branch_id) is None:
            raise HTTPException(404, "分支不存在")
        return get_reading_position(connection, branch_id)


@router.put("/{branch_id}/reading-position")
def save_position(branch_id: str, data: ReadingPositionInput, request: Request):
    try:
        with connect(request.app.state.life_db) as connection:
            if get_branch(connection, branch_id) is None:
                raise HTTPException(404, "分支不存在")
            save_reading_position(connection, branch_id=branch_id, **data.model_dump())
            return get_reading_position(connection, branch_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
