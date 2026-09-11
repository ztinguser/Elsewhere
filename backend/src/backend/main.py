import uvicorn
from fastapi import FastAPI

from backend.api.health import router as health_router

app = FastAPI(title="Elsewhere", docs_url=None, redoc_url=None)
app.include_router(health_router, prefix="/api")


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)