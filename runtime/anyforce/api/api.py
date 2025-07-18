import asyncio
from copy import copy
from datetime import datetime
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Generic,
    Iterable,
    Type,
    TypeVar,
    cast,
)

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel as PydanticBaseModel
from pydantic import create_model
from pypika_tortoise.functions import Count
from pypika_tortoise.terms import Field as pikaField
from pypika_tortoise.terms import Term
from tortoise.expressions import Function, Q, RawSQL
from tortoise.fields.base import Field
from tortoise.models import MetaInfo
from tortoise.queryset import CountQuery, QuerySet

from .. import json
from ..model import BaseModel
from ..model.functions import in_transaction
from .exceptions import (
    HTTPForbiddenError,
    HTTPNotFoundError,
    HTTPPreconditionRequiredError,
)

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
    id: str | int | None = None


class API(Generic[UserModel, Model, CreateForm, UpdateForm]):
    def __init__(
        self,
        model: Type[Model],
        create_form: Type[CreateForm],
        update_form: Type[UpdateForm],
        get_current_user: Callable[..., Coroutine[Any, Any, UserModel] | UserModel],
        enable_create: bool = True,
        enable_update: bool = True,
        enable_delete: bool = True,
        enable_get: bool = True,
        enable_summary: bool = False,
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
        self.enable_summary = enable_summary

    async def translate_id(self, user: UserModel, id: str, request: Request) -> str:
        return id

    def translate_order_by(
        self, user: UserModel, ordering: str, request: Request
    ) -> list[str]:
        return [self.model.normalize_field(ordering)]

    async def translate_condition(
        self, user: UserModel, q: QuerySet[Model], k: str, v: Any, request: Request
    ) -> Any:
        return v

    def group_by_f(self, group_by: str, field: Field[Any]) -> Function | Term | None:
        return None

    def group_by(
        self,
        user: UserModel,
        q: QuerySet[Model],
        include: Iterable[str],
        group_by: list[str],
        order_by: list[str],
    ):
        model_meta: MetaInfo = getattr(q.model, "_meta")
        fields_map: dict[str, Field[Any]] = getattr(model_meta, "fields_map")
        field_names: Iterable[str] = include or fields_map.keys()
        annotates: dict[str, Function | Term] = {}
        for field_name in field_names:
            if field_name in group_by:
                continue
            field = fields_map[field_name]
            annotate = self.group_by_f(field_name, field)
            if annotate is None:
                continue

            group_by_name = f"_{field_name}_"
            annotates[group_by_name] = annotate

            # order_by
            for i, o in enumerate(order_by):
                if o == field_name or o == f"-{field_name}":
                    order_by[i] = o.replace(field_name, group_by_name)

        q = q.annotate(**annotates)
        q = q.group_by(*group_by)
        return q

    async def grouping(
        self,
        user: UserModel,
        q: QuerySet[Model],
        include: Iterable[str],
        group_by: list[str],
        order_by: list[str] = [],
    ) -> list[Model]:
        return await self.grouping_q(
            self.group_by(user, q, include, group_by, order_by), group_by
        )

    async def grouping_q(
        self,
        q: QuerySet[Model],
        group_by: list[str],
    ) -> list[Model]:
        group_q = q.filter()
        setattr(group_q, "_fields_for_select", tuple())
        dicts = await group_q.values(
            *set(group_by).union(getattr(q, "_annotations").keys())
        )
        es: list[Model] = []
        # overwrite default value
        kwargs: dict[str, str] = {}
        for k, field in self.model.fields_map().items():
            if field.default and isinstance(field.default, str):
                kwargs[k] = ""
        for dic in dicts:
            e = self.model()
            for k, v in dic.items():
                if v is None:
                    continue
                k = k[1:-1] if k.startswith("_") and k.endswith("_") else k
                setattr(e, k, v)
            es.append(e)
        return es

    async def excludes(self, method: ResourceMethod) -> set[str] | None:
        return None

    async def q(
        self,
        user: UserModel,
        request: Request,
        q: QuerySet[Model],
        method: ResourceMethod,
    ) -> QuerySet[Model]:
        excludes = await self.excludes(method)
        if excludes:
            model_meta = getattr(q.model, "_meta")
            fields_db_projection: dict[str, Any] = (
                getattr(model_meta, "fields_db_projection") if model_meta else {}
            )
            include: set[str] = (
                set(
                    getattr(q, "_fields_for_select", None)
                    or fields_db_projection.keys()
                )
                - excludes
            )
            if not include:
                raise HTTPForbiddenError
            q = q.only(*include)
        return q

    async def fetch_related(
        self, obj: Model, method: ResourceMethod, prefetch: list[str]
    ):
        excludes = await self.excludes(method)
        if excludes:
            include_prefetch = set(prefetch) - set(excludes)
            if not include_prefetch:
                return
            prefetch = list(include_prefetch)
        await obj.fetch_related(*prefetch)

    async def before_create(
        self,
        user: UserModel,
        input: CreateForm,
        request: Request,
    ) -> Any:
        return input

    async def before_save(
        self,
        user: UserModel,
        obj: Model,
        input: Any,
        request: Request,
    ) -> Model:
        return obj

    async def after_create(
        self, user: UserModel, obj: Model, input: Any, request: Request
    ) -> Any:
        return obj

    async def before_update(
        self, user: UserModel, obj: Model, input: UpdateForm, request: Request
    ) -> Model | None:
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
        meta: MetaInfo = getattr(self.model, "_meta")
        return meta.default_connection

    async def get(
        self, ids: str, user: UserModel, request: Request, method: ResourceMethod
    ):
        normalize_ids = await asyncio.gather(
            *[self.translate_id(user, id.strip(), request) for id in ids.split(",")]
        )
        objs = await (
            await self.q(
                user,
                request,
                self.model.filter(id__in=normalize_ids),
                method,
            )
        ).all()
        if len(objs) != len(normalize_ids):
            raise HTTPNotFoundError
        return objs

    async def translate_kv_condition(
        self, user: UserModel, request: Request, q: QuerySet[Model], kv: dict[str, Any]
    ) -> tuple[QuerySet[Model], Q]:
        join_infos: dict[str, tuple[str, bool]] = {
            ".and": (Q.AND, False),
            ".or": (Q.OR, False),
            ".not": (Q.AND, True),
            ".not_or": (Q.OR, True),
        }

        qs: list[Q] = []
        q_kwargs: dict[str, Any] = {}
        for k, v in kv.items():
            child_join_type, child_reverse = join_infos.get(k, ("", False))
            if child_join_type:
                if isinstance(v, dict):
                    q, iq = await self.translate_kv_condition(
                        user, request, q, cast(dict[str, Any], v)
                    )
                elif isinstance(v, list):
                    cqs: list[Q] = []
                    for cv in cast(list[dict[str, Any]], v):
                        q, ciq = await self.translate_kv_condition(
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
            v = await self.translate_condition(user, q, k, v, request)
            if isinstance(v, QuerySet):
                q = cast(QuerySet[Model], v)
            elif isinstance(v, Q):
                qs.append(v)
            elif (
                v is not None
                and not (isinstance(v, list) and not v)
                and not (isinstance(v, dict) and not v)
            ):
                q_kwargs[k] = v
        kv_q = Q(
            *qs,
            **q_kwargs,
            join_type=Q.AND,
        )
        return q, kv_q

    def bind(self, router: APIRouter):
        list_exclude: set[str] = set(self.model.PydanticMeta.list_exclude or [])
        if not TYPE_CHECKING:
            CreateForm = self.create_form
            UpdateForm = self.update_form
        ListPydanticModel = self.model.list()
        DetailPydanticModel = self.model.detail()

        DetailPydanticModels = list[DetailPydanticModel] | DetailPydanticModel
        Response = create_model(
            f"{self.model.__module__}.{self.model.__name__}.Response",
            __base__=PydanticBaseModel,
            total=(int, 0),
            summary=(ListPydanticModel | None, ...),
            data=(list[ListPydanticModel], ...),
        )

        methods: dict[str, Callable[..., Any]] = {}

        if self.enable_create:

            @router.post(
                "/",
                response_model=DetailPydanticModels,
                response_class=ORJSONResponse,
                status_code=status.HTTP_201_CREATED,
                response_model_exclude_unset=True,
                response_model_exclude_none=True,
            )
            async def create(
                request: Request,
                input: list[CreateForm] | CreateForm = self.get_form_type(
                    self.create_form
                ),
                prefetch: list[str] = self.prefetch_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                async with in_transaction(self.connection_name):
                    is_batch = isinstance(input, list)
                    inputs = input if is_batch else [input]

                    returns: list[PydanticBaseModel] = []
                    for input in inputs:
                        input = await self.before_create(current_user, input, request)
                        raw, computed, m2ms = self.model.process(input)
                        obj = await self.before_save(
                            current_user, self.model(**raw), input, request
                        )
                        await obj.save()
                        await obj.update_computed(computed)
                        await obj.save_m2ms(m2ms)
                        if prefetch:
                            await self.fetch_related(
                                obj, ResourceMethod.create, prefetch
                            )

                        obj_rtn = await self.after_create(
                            current_user, obj, input, request
                        )

                        if obj_rtn:
                            obj = obj_rtn

                        if isinstance(obj, PydanticBaseModel):
                            returns.append(obj)
                        else:
                            returns.append(DetailPydanticModel.model_validate(obj))
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

            @router.get(
                "/",
                response_model=Response,
                response_class=ORJSONResponse,
                response_model_exclude_unset=True,
                response_model_exclude_none=True,
            )
            async def index(
                request: Request,
                offset: int = Query(0, title="分页偏移"),
                limit: int = Query(20, title="分页限额"),
                include_summary: bool = Query(False, title="是否包含summary数据"),
                condition: list[str] = Query([], title="查询条件", description=help),
                order_by: list[str] = Query(
                    [],
                    title="排序",
                    description="支持采用 `order_by=id&order_by=user.id` 形式传入多个",
                ),
                include: list[str] = self.include_query(),
                prefetch: list[str] = self.prefetch_query(),
                group_by: list[str] = self.group_by_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                q = self.model.all()

                if not include and list_exclude:
                    db_fields = set(self.model.fields_db_projection().keys())
                    include = list(db_fields - list_exclude)
                if include:
                    q = q.only(*include)

                q = await self.q(current_user, request, q, ResourceMethod.list)

                # 通用过滤方案
                # https://tortoise-orm.readthedocs.io/en/latest/query.html
                if condition:
                    for raw in condition:
                        kv = json.loads(raw)
                        q, iq = await self.translate_kv_condition(
                            current_user, request, q, kv
                        )
                        q = q.filter(iq)

                summary: Model | None = None
                include_summary = self.enable_summary and include_summary
                if include_summary:
                    objs = await self.grouping(current_user, q, include, [])
                    if objs:
                        summary = objs[0]

                if group_by:
                    group_by_fields = ",".join(
                        [f"COALESCE(`{field}`, '')" for field in group_by]
                    )
                    total_q = q.annotate(
                        total=RawSQL(f"COUNT(DISTINCT {group_by_fields})")
                    ).group_by()
                    setattr(total_q, "_fields_for_select", tuple())
                    r = await total_q.values("total")
                    total = r[0]["total"] if r else 0
                else:
                    total = await DistinctCountQuery(q.count())
                    q = q.distinct()

                q = q.offset(offset).limit(limit)
                if group_by:
                    q = self.group_by(current_user, q, include, group_by, order_by)
                if order_by:
                    orderings: list[str] = []
                    for item in order_by:
                        orderings += self.translate_order_by(
                            current_user, item, request
                        )
                    q = q.order_by(*orderings)

                if group_by:
                    objs = await self.grouping_q(q, group_by)
                else:
                    objs = await q

                if prefetch:
                    for obj in objs:
                        await self.fetch_related(obj, ResourceMethod.list, prefetch)
                    if summary:
                        await self.fetch_related(summary, ResourceMethod.list, prefetch)

                return Response(
                    total=total,
                    summary=summary and ListPydanticModel.model_validate(summary),
                    data=[ListPydanticModel.model_validate(obj) for obj in objs],
                )

            @router.get(
                "/{id}",
                response_model=DetailPydanticModel,
                response_class=ORJSONResponse,
                response_model_exclude_unset=True,
                response_model_exclude_none=True,
            )
            async def get(
                request: Request,
                id: str = Path(..., title="id"),
                prefetch: list[str] = self.prefetch_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                id = await self.translate_id(current_user, id, request)
                q = await self.q(
                    current_user,
                    request,
                    self.model.all().filter(id=id),
                    ResourceMethod.get,
                )
                obj = await q.first()
                if not obj:
                    raise HTTPNotFoundError
                if prefetch:
                    await self.fetch_related(obj, ResourceMethod.get, prefetch)
                return DetailPydanticModel.model_validate(obj)

            methods["index"] = index
            methods["get"] = get

        if self.enable_update:

            @router.put(
                "/{ids}",
                response_model=DetailPydanticModels,
                response_class=ORJSONResponse,
                response_model_exclude_unset=True,
                response_model_exclude_none=True,
            )
            async def update(
                request: Request,
                ids: str = self.ids_path(),
                input: UpdateForm = self.get_form_type(self.update_form),
                prefetch: list[str] = self.prefetch_query(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> Any:
                async with in_transaction(self.connection_name):
                    returns: list[Any] = []
                    excludes = await self.excludes(ResourceMethod.put)
                    for obj in await self.get(
                        ids, current_user, request, ResourceMethod.put
                    ):
                        r = await self.before_update(current_user, obj, input, request)
                        if r:
                            obj = r
                            raw = input.model_dump(exclude_unset=True, exclude=excludes)

                            updated_at = raw.pop("updated_at", None)
                            if updated_at:
                                # 防止老数据修改
                                if isinstance(updated_at, str):
                                    updated_at = json.parse_iso_datetime(updated_at)
                                if isinstance(updated_at, datetime):
                                    obj_updated_at: datetime | None = getattr(
                                        obj, "updated_at", None
                                    )
                                    if obj_updated_at:
                                        # 前端不支持微妙精度
                                        obj_updated_at = obj_updated_at.replace(
                                            microsecond=0
                                        )
                                        assert obj_updated_at
                                        if obj_updated_at > updated_at:
                                            raise HTTPPreconditionRequiredError

                            obj_obj = copy(obj)

                            update_fields = raw.keys()
                            if update_fields:
                                await obj.update(raw)
                                obj = await self.before_save(
                                    current_user, obj, raw, request
                                )
                                await obj.save(update_fields=update_fields)

                            if prefetch:
                                await self.fetch_related(
                                    obj, ResourceMethod.put, prefetch
                                )

                            obj_rtn = await self.after_update(
                                current_user, obj_obj, input, obj, request
                            )
                            if obj_rtn:
                                obj = obj_rtn

                        returns.append(
                            obj
                            if isinstance(obj, PydanticBaseModel)
                            else DetailPydanticModel.model_validate(obj)
                        )
                    return returns if len(returns) > 1 else returns[0]

            methods["update"] = update

        if self.enable_delete:

            @router.delete(
                "/{ids}",
                response_model=list[DeleteResponse] | DeleteResponse,
                response_class=ORJSONResponse,
                response_model_exclude_unset=True,
                response_model_exclude_none=True,
            )
            async def delete(
                request: Request,
                ids: str = self.ids_path(),
                current_user: UserModel = Depends(self.get_current_user),
            ) -> list[DeleteResponse] | DeleteResponse:
                async with in_transaction(self.connection_name):
                    rs: list[DeleteResponse] = []
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


class DistinctCountQuery(CountQuery):
    def __init__(self, q: CountQuery) -> None:
        super().__init__(
            q.model,  # type: ignore
            q._db,
            q._q_objects,
            q._annotations,
            q._custom_filters,
            q._limit,
            q._offset,
            q._force_indexes,
            q._use_indexes,
        )

    def _make_query(self) -> None:
        super()._make_query()
        setattr(
            self.query,
            "_selects",
            [
                Count(pikaField("id", table=self.model._meta.basetable)).distinct()  # type: ignore
            ],
        )
