from fastapi import APIRouter, Request, Response

router = APIRouter()
SESSION_COOKIE = "elsewhere_session"


@router.post("/session", status_code=204)
async def establish_session(request: Request) -> Response:
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.set_cookie(
        SESSION_COOKIE, request.app.state.session_token,
        httponly=True, samesite="strict", path="/",
    )
    return response
