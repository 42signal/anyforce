from typing import Any, Dict, List

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_context.middleware import RawContextMiddleware
from tortoise.contrib.fastapi import register_tortoise

from .api.exceptions import register


def create_app(
    secret_key: str,
    https_only: bool,
    allow_origins: List[str],
    tortoise_config: Dict[str, Any],
):
    app = FastAPI()
    app.add_middleware(RawContextMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=secret_key, https_only=https_only)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register(app)
    register_tortoise(
        app,
        config=tortoise_config,
        generate_schemas=False,
        add_exception_handlers=False,
    )

    @app.get("/healthz")
    async def _() -> str:
        return ""

    return app
