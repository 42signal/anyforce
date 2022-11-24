from typing import Any, Dict, List, Optional, Type, cast
from weakref import WeakKeyDictionary

from fastapi import FastAPI
from pydantic import BaseModel
from pydantic.fields import ModelField
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_context.middleware import RawContextMiddleware
from tortoise.contrib.fastapi import register_tortoise

from .api.exceptions import register

# TODO: remove after fastapi resolve https://github.com/tiangolo/fastapi/issues/4644
cloned_types_default: Dict[Type[BaseModel], Type[BaseModel]] = cast(
    Dict[Type[BaseModel], Type[BaseModel]], WeakKeyDictionary()
)


def patch_fastapi_create_cloned_field() -> None:
    import fastapi.routing
    import fastapi.utils

    orig = fastapi.utils.create_cloned_field

    def patch(
        field: ModelField,
        *,
        cloned_types: Optional[Dict[Type[BaseModel], Type[BaseModel]]] = None,
    ) -> ModelField:
        return orig(
            field,
            cloned_types=cloned_types_default if cloned_types is None else cloned_types,
        )

    setattr(fastapi.utils, "create_cloned_field", patch)
    setattr(fastapi.routing, "create_cloned_field", patch)


patch_fastapi_create_cloned_field()


def create_app(
    secret_key: str,
    allow_origins: List[str],
    tortoise_config: Dict[str, Any],
    max_age: int = 14 * 24 * 60 * 60,
    same_site: str = "lax",
    https_only: bool = True,
):
    app = FastAPI()
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
