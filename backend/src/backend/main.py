from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

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
    app.include_router(health_router, prefix="/api")
    return app


def main() -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, access_log=False)