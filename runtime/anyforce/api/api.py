import asyncio
from copy import copy
from datetime import datetime
from enum import IntEnum
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel as PydanticBaseModel
from pydantic import create_model
from pypika.terms import Term
from tortoise.expressions import RawSQL
from tortoise.functions import Function
from tortoise.models import Field, MetaInfo
from tortoise.queryset import Q, QuerySet
from tortoise.transactions import in_transaction

from .. import json
from ..model import BaseModel
from .exceptions import HTTPNotFoundError, HTTPPreconditionRequiredError

UserModel = TypeVar("UserModel")
Model = TypeVar("Model", bound=BaseModel)
CreateForm = TypeVar("CreateForm", bound=PydanticBaseModel)
UpdateForm = TypeVar("UpdateForm", bound=PydanticBaseModel)


class ResourceMethod(IntEnum):
    list = 0
    get = 1
    create = 2
    put = 3
    delete = 4


class DeleteResponse(PydanticBaseModel):
    id: Optional[Union[str, int]]


class API(Generic[UserModel, Model, CreateForm, UpdateForm]):
    def __init__(
        self,
        model: Type[Model],
        create_form: Type[CreateForm],
        update_form: Type[UpdateForm],
        get_current_user: Callable[
            ..., Union[Coroutine[Any, Any, UserModel], UserModel]
        ],
        enable_create: bool = True,
        enable_update: bool = True,
        enable_delete: bool = True,
        enable_get: bool = True,
    ) -> None:
        super().__init__()
        self.model = model
        self.create_form = create_form
        self.update_form = update_form
        self.get_current_user = get_current_user
        self.enable_create = enable_create
        self.enable_update = enable_update
        self.enable_delete = enable_delete
        self.enable_get = enable_get

    async def translate_id(self, user: UserModel, id: str, request: Request) -> str:
        return id

    def translate_order_by(
        self, user: UserModel, ordering: str, request: Request
    ) -> List[str]:
        return [self.model.normalize_field(ordering)]

    def translate_condition(
        self, user: UserModel, q: QuerySet[Model], k: str, v: Any, request: Request
    ) -> Any:
        return v

    def group_by_f(
        self, group_by: str, field: Field
    ) -> Optional[Union[Function, Term]]:
        return None

    def group_by(
        self,
        user: UserModel,
        q: QuerySet[Model],
        include: Iterable[str],
        group_by: List[str],
    ):
        model_meta: MetaInfo = getattr(q.model, "_meta")
        field_names: Iterable[str] = include or model_meta.fields_map.keys()
        annotates: Dict[str, Union[Function, Term]] = {}
        for field_name in field_names:
            if field_name in group_by:
                continue
            field = model_meta.fields_map[field_name]
            annotate = self.group_by_f(field_name, field)
            if annotate is None:
                continue
            annotates[field_name] = annotate
        q = q.annotate(**annotates)
        q = q.group_by(*group_by)
        return annotates, q

    def q(
        self,
        user: UserModel,
        request: Request,
        q: QuerySet[Model],
        method: ResourceMethod,
    ) -> QuerySet[Model]:
        return q

    async def before_create(
        self,
        user: UserModel,
        obj: Model,
        input: CreateForm,
        request: Request,
    ) -> Model:
        return obj

    async def after_create(
        self, user: UserModel, obj: Model, input: CreateForm, request: Request
    ) -> Any:
        return obj

    async def before_update(
        self, user: UserModel, obj: Model, input: UpdateForm, request: Request
    ) -> Optional[Model]:
        return obj

    async def after_update(
        self,
        user: UserModel,
        old_obj: Model,
        input: UpdateForm,
        obj: Model,
        request: Request,
    ) -> Any:
        return obj

    async def before_delete(
        self, user: UserModel, obj: Model, request: Request
    ) -> Model:
        return obj

    @classmethod
    def ids_path(cls):
        return Path(..., title="ID", description="支持采用 `1,2,3` 形式传入多个")

    @classmethod
    def include_query(cls):
        return Query(
            [],
            title="只获取某些字段",
            description="支持采用 `include=id&include=name` 形式传入多个",
        )

    @classmethod
    def prefetch_query(cls):
        return Query(
            [],
            title="动态加载计算字段",
            description="获取更多字段, 支持采用 `prefetch=id&prefetch=user.id` 形式传入多个",
        )

    @classmethod
    def group_by_query(cls):
        return Query(
            [],
            title="分组",
            description="分组, 不在分组字段默认为 MAX, 支持采用 `group_by=x&group_by=y` 形式传入多个",
        )

    @classmethod
    def get_form_type(cls, form: Any) -> Any:
        f = getattr(form, "form_type", None)
        return f and f() or Body(...)

    @property
    def connection_name(self):
        return self.model._meta.default_connection  # type: ignore

    async def get(
        self, ids: str, user: UserModel, request: Request, method: ResourceMethod
    ):
        normalize_ids = await asyncio.gather(
            *[self.translate_id(user, id.strip(), request) for id in ids.split(",")]
        )
        objs = await self.q(
            user,
            request,
            self.model.filter(id__in=normalize_ids),
            method,
        ).all()
        if len(objs) != len(normalize_ids):
            raise HTTPNotFoundError
        return objs

    def translate_kv_condition(
        self, user: UserModel, request: Request, q: QuerySet[Model], kv: Dict[str, Any]
    ):
        join_infos: Dict[str, Tuple[str, bool]] = {
            ".and": (Q.AND, False),
            ".or": (Q.OR, False),
            ".not": (Q.AND, True),
            ".not_or": (Q.OR, True),
        }

        qs: List[Q] = []
        q_kwargs: Dict[str, Any] = {}
        for k, v in kv.items():
            child_join_type, child_reverse = join_infos.get(k, ("", False))
            if child_join_type:
                if isinstance(v, dict):
                    q, iq = self.translate_kv_condition(
                        user, request, q, cast(Dict[str, Any], v)
                    )
                elif isinstance(v, list):
                    cqs: List[Q] = []
                    for cv in cast(List[Dict[str, Any]], v):
                        q, ciq = self.translate_kv_condition(
                            user,
                            request,
                            q,
                            cv,
                        )
                        cqs.append(ciq)
                    iq = Q(*cqs)
                else:
                    assert False
                iq.join_type = child_join_type
                if child_reverse:
                    iq = ~iq
                qs.append(iq)
                continue

            k = self.model.normalize_field(k)
            v = self.translate_condition(user, q, k, v, request)
            if isinstance(v, QuerySet):
                q = cast(QuerySet[Model], v)
            elif isinstance(v, Q):
                qs.append(v)
            elif (
                v is not None
                and v != ""
                and not (isinstance(v, list) and not v)
                and not (isinstance(v, dict) and not v)
            ):
                if v == "$empty":
                    v = ""
                q_kwargs[k] = v
        kv_q = Q(
            *qs,
            **q_kwargs,
            join_type=Q.AND,
        )
        return q, kv_q

    def bind(self, router: APIRouter):
        ListPydanticModel = self.model.list()
        DetailPydanticModel = self.model.detail()
        CreateForm = self.create_form
        UpdateForm = self.update_form

        DetailPydanticModels = Union[
            DetailPydanticModel, List[DetailPydanticModel]  # type: ignore
        ]
        Response = create_model(
            f"{self.model.__module__}.{self.model.__name__}.Response",
            __base__=PydanticBaseModel,
            total=0,
            data=(List[ListPydanticModel], ...),  # type: ignore
        )

        methods: Dict[str, Callable[..., Any]] = {}

        if self.enable_create:

            @router.post(
                "/",
                response_model=DetailPydanticModels,
                response_class=ORJSONResponse,
                status_code=status.HTTP_201_CREATED,
            )
            async def create(
                request: Request,
                input: Union[List[CreateForm], CreateForm] = self.get_form_type(
                    CreateForm
                ),
                prefetch: List[str] = self.prefetch_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                async with in_transaction(self.connection_name):
                    is_batch = isinstance(input, list)
                    inputs = cast(List[CreateForm], input if is_batch else [input])

                    returns: List[PydanticBaseModel] = []
                    for input in inputs:
                        raw, m2ms = self.model.process(input)
                        obj = self.model(**raw)

                        obj = await self.before_create(
                            current_user, obj, input, request
                        )
                        await obj.save()
                        await obj.save_m2ms(m2ms)
                        if prefetch:
                            await obj.fetch_related(*prefetch)

                        obj_rtn = await self.after_create(
                            current_user, obj, input, request
                        )
                        if obj_rtn:
                            obj = obj_rtn

                        if isinstance(obj, PydanticBaseModel):
                            returns.append(obj)
                        else:
                            returns.append(DetailPydanticModel.from_orm(obj))
                    return returns if is_batch else returns[0]

            methods["create"] = create

        if self.enable_get:
            help = """支持采用 `condition=...&condition=...` 传入多个, 使用 JSON 序列化
[查询语法参考](https://tortoise-orm.readthedocs.io/en/latest/query.html#filtering)

###### 简单查询

```javascript
{
    "email": "name@example.com",
    "name.contains": "name",
    "id.in": [1, 2, 3],
}
```

###### 跨表查询

```javascript
{
    "user.email": "name@example.com",
    "user.name.contains": "name",
}
```

###### 子逻辑, 可选项: `.and` `.or` `.not` `.not_or`

```javascript
// (name contains name2 or email contains example2.com)
{
    ".or": {
        "name.contains": "name2",
        "email.contains": "example2.com",
    },
    "name.contains": "name",
    "email.contains": "example.com",
}

// (name contains name2 and email contains example2.com) or (name contains name3)
{
    ".or": [{
        "name.contains": "name2"
        "email.contains": "example2.com",
    }, {
        "name.contains": "name3",
    }],
    "name.contains": "name",
    "email.contains": "example.com",
}
```
            """

            @router.get("/", response_model=Response, response_class=ORJSONResponse)
            async def index(
                request: Request,
                offset: int = Query(0, title="分页偏移"),
                limit: int = Query(20, title="分页限额"),
                condition: List[str] = Query([], title="查询条件", description=help),
                order_by: List[str] = Query(
                    [],
                    title="排序",
                    description="支持采用 `order_by=id&order_by=user.id` 形式传入多个",
                ),
                include: List[str] = self.include_query(),
                prefetch: List[str] = self.prefetch_query(),
                group_by: List[str] = self.group_by_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                q = self.model.all()
                q = self.q(current_user, request, q, ResourceMethod.list)

                # 通用过滤方案
                # https://tortoise-orm.readthedocs.io/en/latest/query.html
                if condition:
                    for raw in condition:
                        kv = cast(Any, json.loads(raw))
                        q, iq = self.translate_kv_condition(
                            current_user, request, q, kv
                        )
                        q = q.filter(iq)

                if include:
                    q = q.only(*include)

                if group_by:
                    group_by_fields = ",".join([f"`{field}`" for field in group_by])
                    total_q = q.annotate(
                        total=RawSQL(f"COUNT(DISTINCT {group_by_fields})")
                    ).values("total")
                    total_q.group_bys = tuple()
                    r = cast(List[Dict[str, int]], await total_q)
                    total = r[0]["total"] if r else 0
                else:
                    q = q.distinct()
                    total = await q.count()

                if order_by:
                    orderings: List[str] = []
                    for item in order_by:
                        orderings += self.translate_order_by(
                            current_user, item, request
                        )
                    q = q.order_by(*orderings)

                q = q.offset(offset).limit(limit)
                if group_by:
                    annotates, q = self.group_by(current_user, q, include, group_by)
                    dicts = cast(
                        List[Dict[str, Any]],
                        await q.values(*group_by, *annotates.keys()),
                    )
                    objs = [self.model(**v) for v in dicts]
                else:
                    objs = await q

                if prefetch:
                    for obj in objs:
                        await obj.fetch_related(*prefetch)

                return Response(
                    total=total,
                    data=[ListPydanticModel.from_orm(obj) for obj in objs],
                )

            @router.get(
                "/{id}",
                response_model=DetailPydanticModel,
                response_class=ORJSONResponse,
            )
            async def get(
                request: Request,
                id: str = Path(..., title="id"),
                prefetch: List[str] = self.prefetch_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                id = await self.translate_id(current_user, id, request)
                q = self.q(
                    current_user,
                    request,
                    self.model.all().filter(id=id),
                    ResourceMethod.get,
                )
                obj = await q.first()
                if not obj:
                    raise HTTPNotFoundError
                if prefetch:
                    await obj.fetch_related(*prefetch)
                return DetailPydanticModel.from_orm(obj)

            methods["index"] = index
            methods["get"] = get

        if self.enable_update:

            @router.put(
                "/{ids}",
                response_model=DetailPydanticModels,
                response_class=ORJSONResponse,
            )
            async def update(
                request: Request,
                ids: str = self.ids_path(),
                input: UpdateForm = self.get_form_type(UpdateForm),
                prefetch: List[str] = self.prefetch_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                async with in_transaction(self.connection_name):
                    rtns: List[Any] = []
                    for obj in await self.get(
                        ids, current_user, request, ResourceMethod.put
                    ):
                        r = await self.before_update(current_user, obj, input, request)
                        if r:
                            obj = r
                            raw = input.dict(exclude_unset=True)

                            updated_at = raw.pop("updated_at", None)
                            if updated_at:
                                # 防止老数据修改
                                if isinstance(updated_at, str):
                                    updated_at = json.parse_iso_datetime(updated_at)
                                if isinstance(updated_at, datetime):
                                    obj_updated_at: Optional[datetime] = getattr(
                                        obj, "updated_at", None
                                    )
                                    if obj_updated_at:
                                        obj_updated_at = obj_updated_at.replace(
                                            microsecond=int(
                                                str(obj_updated_at.microsecond)[:3]
                                            )
                                        )
                                        if obj_updated_at > updated_at:
                                            raise HTTPPreconditionRequiredError

                            obj_obj = copy(obj)

                            update_fields = raw.keys()
                            if update_fields:
                                await obj.update(raw)
                                await obj.save(update_fields=update_fields)

                            if prefetch:
                                await obj.fetch_related(*prefetch)

                            obj_rtn = await self.after_update(
                                current_user, obj_obj, input, obj, request
                            )
                            if obj_rtn:
                                obj = obj_rtn

                        rtns.append(
                            obj
                            if isinstance(obj, PydanticBaseModel)
                            else DetailPydanticModel.from_orm(obj)
                        )
                    return len(rtns) > 1 and rtns or rtns[0]

            methods["update"] = update

        if self.enable_delete:

            @router.delete(
                "/{ids}",
                response_model=Union[List[DeleteResponse], DeleteResponse],
                response_class=ORJSONResponse,
            )
            async def delete(
                request: Request,
                ids: str = self.ids_path(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Union[List[DeleteResponse], DeleteResponse]:
                async with in_transaction(self.connection_name):
                    rs: List[DeleteResponse] = []
                    for obj in await self.get(
                        ids, current_user, request, ResourceMethod.delete
                    ):
                        obj = await self.before_delete(current_user, obj, request)
                        await obj.delete()
                        rs.append(DeleteResponse(id=obj.id))
                    return len(rs) > 1 and rs or rs[0]

            methods["delete"] = delete

        return methods


def get_anonymous_user() -> str:
    return "anonymous"


class PublicAPI(API[str, Model, CreateForm, UpdateForm]):
    def __init__(
        self,
        model: Type[Model],
        create_form: Type[CreateForm],
        update_form: Type[UpdateForm],
        enable_create: bool = True,
        enable_update: bool = True,
        enable_delete: bool = True,
        enable_get: bool = True,
    ) -> None:
        super().__init__(
            model,
            create_form=create_form,
            update_form=update_form,
            get_current_user=get_anonymous_user,
            enable_create=enable_create,
            enable_update=enable_update,
            enable_delete=enable_delete,
            enable_get=enable_get,
        )
