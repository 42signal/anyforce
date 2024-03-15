import asyncio
import inspect
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Literal, Sequence

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
    same_site: Literal["lax", "strict", "none"] = "lax",
    https_only: bool = True,
    shutdown_delay_in_seconds: int = 15,
    on_startup: Sequence[Callable[[], Any]] = [],
    on_shutdown: Sequence[Callable[[], Any]] = [],
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init(tortoise_config)
        for c in on_startup:
            cr = c()
            if inspect.isawaitable(cr):
                await cr
        yield
        state[0] = False
        await asyncio.sleep(shutdown_delay_in_seconds)
        await Tortoise.close_connections()
        for c in on_shutdown:
            cr = c()
            if inspect.isawaitable(cr):
                await cr

    app = FastAPI(lifespan=lifespan)

    state: List[bool] = [True]

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
