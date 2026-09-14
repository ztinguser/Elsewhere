from fastapi import APIRouter, HTTPException, Query, Request, Response

from backend.models.drafts import DraftInput
from backend.storage.database import connect
from backend.storage.drafts import delete_draft, get_draft, save_draft


router = APIRouter(prefix="/drafts")


@router.get("/{draft_id}")
def read_draft(draft_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        draft = get_draft(connection, draft_id)

    if draft is None:
        raise HTTPException(404, "草稿不存在")

    return draft


@router.put("/{draft_id}")
def write_draft(
    draft_id: str, data: DraftInput, request: Request
) -> dict:
    try:
        with connect(request.app.state.life_db) as connection:
            revision = save_draft(
                connection,
                draft_id,
                data.content,
                time_text=data.time_text,
                expected_revision=data.expected_revision,
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return {"id": draft_id, "revision": revision}


@router.delete("/{draft_id}", status_code=204)
def remove_draft(
    draft_id: str,
    request: Request,
    expected_revision: int = Query(ge=1),
) -> Response:
    try:
        with connect(request.app.state.life_db) as connection:
            delete_draft(
                connection,
                draft_id,
                expected_revision=expected_revision,
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return Response(status_code=204)