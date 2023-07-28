from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union, cast

from dateutil.parser import parse
from fastapi import Path, Query, Request
from fastapi.param_functions import Depends
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel as PydanticBaseModel
from tortoise import Tortoise
from tortoise.transactions import in_transaction

from ...asyncio import coro
from ...json import loads
from ...logging import getLogger
from ...model import BaseModel
from ..api import DeleteResponse, Model
from .typing import Response, Worker

logger = getLogger(__name__)


@coro
async def update(
    app: str,
    name: str,
    q: Dict[str, Any],
    form: Dict[str, Any],
    context: Dict[str, str],
):
    logger.with_field(context=context).info("update")
    model = Tortoise.apps[app][name]
    async with in_transaction(app):
        obj = (
            await model.filter(**{k: v for k, v in q.items()}).select_for_update().get()
        )
        assert isinstance(obj, BaseModel)
        await obj.update(form)
        await obj.save(update_fields=form.keys())


class Scheduler(object):
    def __init__(
        self,
        worker: Worker,
        schedule_update_at_key: str = "schedule_update_at",
        context_query_keys: List[str] = [],
    ) -> None:
        super().__init__()
        self.worker = worker
        self.schedule_update_at_key = schedule_update_at_key
        self.context_query_keys = context_query_keys

    def bind(
        self,
        router: APIRouter,
        depend: Callable[..., Union[Coroutine[Any, Any, Any], Any]],
    ):
        @router.get("/", response_class=ORJSONResponse)
        def list(
            offset: int = Query(0, title="分页偏移"),
            limit: int = Query(20, title="分页限额"),
            condition: str = Query(
                [], title="查询条件", description='{ "{context_k}": "v" }'
            ),
            _: Any = Depends(depend),
        ) -> Response:
            return self.worker.list(
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
        context_keys: List[str] = ["name"],
    ) -> Optional[Model]:
        schedule_at = request.query_params.get(self.schedule_update_at_key)

        if schedule_at:
            schedule_at = parse(schedule_at)
            assert isinstance(schedule_at, datetime)
            schedule_at = schedule_at.astimezone()

            form = input.dict(exclude_unset=True)
            assert form

            meta = obj.__class__._meta  # type: ignore
            pk_attr = meta.pk_attr
            pk_v = getattr(obj, pk_attr, None)
            assert pk_v
            q = {pk_attr: pk_v}

            context: Dict[str, str] = q.copy()
            for k in context_keys:
                v = getattr(obj, k, None)
                if v is not None:
                    context[k] = v
            for k in self.context_query_keys:
                v = request.query_params.get(k, None)
                if v is not None:
                    context[k] = v

            self.worker.enqueue_at(
                schedule_at,
                update,
                app=meta.app,
                name=obj.__class__.__name__,
                q=q,
                form=form,
                context=context,
            )
            return None
        return obj
