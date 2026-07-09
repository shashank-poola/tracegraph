"""FastAPI entrypoint for the tracegraph.

Run locally:  uv run uvicorn src.main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.routes import router
from src.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="tracegraph", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "tracegraph", "docs": "/docs"}


def main() -> None:
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()