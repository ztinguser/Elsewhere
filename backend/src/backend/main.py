import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from backend.api.errors import http_error, validation_error
from backend.api.health import router as health_router
from backend.api.middleware import track_request
from backend.api.security import check_source
from backend.config import Settings
from backend.storage.migrations import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_dir = app.state.settings.data_dir
    app.state.life_db = data_dir / "life.sqlite"
    app.state.workflow_db = data_dir / "workflow.sqlite"

    initialize_database(app.state.life_db)
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

    app.middleware("http")(check_source)
    app.middleware("http")(track_request)

    app.include_router(health_router, prefix="/api")
    return app


def main() -> None:
    logger = logging.getLogger("elsewhere")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.propagate = False

    uvicorn.run(create_app(), host="127.0.0.1", port=8000, access_log=False)