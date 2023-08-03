import asyncio
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_context.middleware import RawContextMiddleware
from tortoise import Tortoise

from .api.exceptions import register
from .model import init


def create_app(
    secret_key: str,
    allow_origins: List[str],
    tortoise_config: Dict[str, Any],
    max_age: int = 14 * 24 * 60 * 60,
    same_site: str = "lax",
    https_only: bool = True,
    shutdown_delay_in_seconds: int = 15,
):
    app = FastAPI()

    state: List[bool] = [True]

    @app.on_event("startup")
    async def _():
        await init(tortoise_config)

    @app.on_event("shutdown")
    async def _():
        state[0] = False
        await asyncio.sleep(shutdown_delay_in_seconds)
        await Tortoise.close_connections()

    app.add_middleware(RawContextMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        max_age=max_age,
        https_only=https_only,
        same_site=same_site,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register(app)

    @app.get("/healthz")
    async def _() -> str:
        if not state[0]:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE)
        return ""

    return app
