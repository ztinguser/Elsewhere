from fastapi import APIRouter, HTTPException, Request

from backend.models.life_archive import ArchiveConfirm
from backend.storage.database import connect
from backend.storage.life_archive import confirm_archive, get_archive


router = APIRouter(prefix="/life/archive")


@router.get("")
def read_archive(request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        return get_archive(connection)


@router.post("/confirm")
def confirm_life_archive(data: ArchiveConfirm, request: Request) -> dict:
    try:
        with connect(request.app.state.life_db) as connection:
            result = confirm_archive(
                connection,
                expected_revision=data.expected_revision,
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return result