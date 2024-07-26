from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional, Union, cast

from dateutil.parser import parse
from fastapi import Path, Query, Request
from fastapi.param_functions import Depends
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel as PydanticBaseModel
from tortoise import Tortoise
from tortoise.models import MetaInfo
from tortoise.transactions import in_transaction

from ...coro import run
from ...json import loads
from ...logging import getLogger
from ...model import BaseModel
from ..api import DeleteResponse, Model
from .typing import Response, Worker

logger = getLogger(__name__)


@run
async def update(
    app: str,
    model: str,
    q: Dict[str, Any],
    form: Dict[str, Any],
):
    logger.with_field(app=app, model=model, q=q, form=form).info("update")
    model_cls = Tortoise.apps[app][model]
    async with in_transaction(app):
        obj = (
            await model_cls.filter(**{k: v for k, v in q.items()})
            .select_for_update()
            .get()
        )
        assert isinstance(obj, BaseModel)
        await obj.update(form)
        await obj.save(update_fields=form.keys())


class Scheduler(object):
    def __init__(
        self,
        worker: Worker,
        schedule_update_at_key: str = "schedule_update_at",
    ) -> None:
        super().__init__()
        self.worker = worker
        self.schedule_update_at_key = schedule_update_at_key

    def bind(
        self,
        router: APIRouter,
        depend: Callable[..., Union[Coroutine[Any, Any, Any], Any]],
    ):
        @router.get("/", response_class=ORJSONResponse)
        async def list(
            offset: int = Query(0, title="分页偏移"),
            limit: int = Query(20, title="分页限额"),
            condition: str = Query(
                [], title="查询条件", description='{ "{context_k}": "v" }'
            ),
            _: Any = Depends(depend),
        ) -> Response:
            return await self.worker.list(
                offset, limit, cast(Dict[str, str], loads(condition))
            )

        @router.delete("/{id}", response_class=ORJSONResponse)
        async def delete(
            id: str = Path(..., title="ID"),
            _: Any = Depends(depend),
        ) -> DeleteResponse:
            self.worker.cancel(id)
            return DeleteResponse(id=id)

        logger.with_field(list=list, delete=delete).info("bind")

        return router

    def before_update(
        self,
        obj: Model,
        input: PydanticBaseModel,
        request: Request,
    ) -> Optional[Model]:
        schedule_at = request.query_params.get(self.schedule_update_at_key)

        if schedule_at:
            schedule_at = parse(schedule_at)
            assert isinstance(schedule_at, datetime)
            schedule_at = schedule_at.astimezone()

            form = input.model_dump(exclude_unset=True)
            assert form

            meta: MetaInfo = getattr(obj.__class__, "_meta")
            pk_attr = meta.pk_attr
            pk_v = getattr(obj, pk_attr, None)
            assert pk_v
            q = {pk_attr: pk_v}

            self.worker.enqueue_at(
                schedule_at,
                update,
                app=meta.app,
                model=obj.__class__.__name__,
                q=q,
                form=form,
            )
            return None
        return obj
