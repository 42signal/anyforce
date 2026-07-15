from datetime import datetime
from typing import Any, cast

import pytest
from fastapi import APIRouter, BackgroundTasks, FastAPI, Request
from pydantic import AnyUrl, EmailStr
from tortoise.queryset import QuerySet

from anyforce.api import PublicAPI

from .model import Model2, name

pytest_plugins = [
    "anyforce.test.fixtures",
]


@pytest.fixture(scope="session")
def models():
    return [name]


@pytest.fixture(scope="session")
def router(app: FastAPI):
    class CreateForm(Model2.form()):
        text_field: AnyUrl

    class UpdateForm(Model2.form(required_override=False)):
        text_field: EmailStr | None = None

    class API(PublicAPI[Model2, CreateForm, UpdateForm]):
        def __init__(self) -> None:
            super().__init__(Model2, CreateForm, UpdateForm)

        async def translate_condition(
            self,
            user: str,
            q: QuerySet[Model2],
            k: str,
            v: Any,
            request: Request,
        ) -> Any:
            if k == "datetime_field__range":
                assert isinstance(v, list)
                assert all(isinstance(item, datetime) for item in cast(list[Any], v))
            return await super().translate_condition(user, q, k, v, request)

        async def after_create(
            self,
            user: str,
            obj: Model2,
            input: CreateForm,
            request: Request,
            background_tasks: BackgroundTasks,
        ) -> Any:
            obj = await super().after_create(
                user, obj, input, request, background_tasks
            )
            if obj.id == 1:
                return Model2.detail().model_validate(obj)

        async def after_update(
            self,
            user: str,
            old_obj: Model2,
            input: UpdateForm,
            obj: Model2,
            request: Request,
            background_tasks: BackgroundTasks,
        ) -> Any:
            obj = await super().after_update(
                user, old_obj, input, obj, request, background_tasks
            )
            if obj.id == 1:
                return Model2.detail().model_validate(obj)

        async def before_delete(
            self,
            user: str,
            obj: Model2,
            request: Request,
        ) -> Any:
            obj = await super().before_delete(user, obj, request)
            new_obj = await Model2.filter(id=obj.id).first()
            assert new_obj
            return new_obj

    router = APIRouter(prefix="/models")
    API().bind(router)
    app.include_router(router)
    return router
