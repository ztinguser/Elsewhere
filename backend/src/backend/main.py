from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from backend.api.errors import http_error, server_error, validation_error
from backend.api.health import router as health_router
from backend.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Elsewhere",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings if settings is not None else Settings()

    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(Exception, server_error)

    app.include_router(health_router, prefix="/api")
    return app


def main() -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, access_log=False)