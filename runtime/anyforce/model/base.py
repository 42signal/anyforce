import inspect
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple, Type, cast

from tortoise import Tortoise
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.contrib.pydantic.base import PydanticModel
from tortoise.contrib.pydantic.creator import (
    pydantic_model_creator,  # type: ignore
)
from tortoise.contrib.pydantic.creator import PydanticMeta
from tortoise.fields.base import Field
from tortoise.fields.relational import ManyToManyFieldInstance
from tortoise.models import Model

from .fields import IntField, LocalDatetimeField
from .patch import patch_pydantic


class BaseModel(Model):
    id: int = IntField(pk=True)
    created_at: datetime = LocalDatetimeField(null=False, auto_now_add=True, index=True)

    class Meta:
        abstract = True

    class PydanticMeta:
        max_recursion = 1

    #     computed: Tuple[str, ...] = ()  # 计算量, 异步计算量返回值需要标记为 Optional
    #     form_exclude: Tuple[str, ...] = ()  # 表单排除
    #     list_exclude: Tuple[str, ...] = ()  # 列表排除

    class FormPydanticMeta(PydanticMeta):
        computed: Tuple[str, ...] = tuple()  # 计算量不能作为 form 传入, 模拟可编辑时可覆盖

    async def dict(self, prefetch: Optional[List[str]] = None) -> Dict[str, Any]:
        if prefetch:
            await self.fetch_related(*prefetch)
        return self.detail().from_orm(self).dict()

    @classmethod
    async def update_or_create(
        cls,
        defaults: Optional[Dict[str, Any]] = None,
        using_db: Optional[BaseDBAsyncClient] = None,
        **kwargs: Any,
    ):
        return (
            await super().update_or_create(  # pyright: ignore[reportUnknownMemberType]
                defaults=defaults, using_db=using_db, **kwargs
            )
        )

    @classmethod
    def list_exclude(cls) -> Optional[Tuple[str, ...]]:
        return getattr(cls.PydanticMeta, "list_exclude", None)

    @classmethod
    def fields_map(cls) -> Dict[str, Field[Any]]:
        model_meta = getattr(cls, "_meta")
        return getattr(model_meta, "fields_map") if model_meta else {}

    @classmethod
    def fields_db_projection(cls) -> Dict[str, str]:
        model_meta = getattr(cls, "_meta")
        return getattr(model_meta, "fields_db_projection") if model_meta else {}

    @classmethod
    @lru_cache
    def list(cls) -> Type[PydanticModel]:
        return cls.make_pydantic(
            name="list", required_override=False, exclude=cls.list_exclude()
        )

    @classmethod
    @lru_cache
    def detail(
        cls,
        required_override: Optional[bool] = None,
        from_models: Tuple[str, ...] = (),
    ) -> Type[PydanticModel]:
        return cls.make_pydantic(
            name="detail",
            required_override=required_override,
            from_models=from_models,
        )

    @classmethod
    @lru_cache
    def form(
        cls,
        required_override: Optional[bool] = None,
        from_models: Tuple[str, ...] = (),
    ) -> Type[PydanticModel]:
        meta: Optional[PydanticMeta] = getattr(cls, "PydanticMeta", None)
        form_exclude: Tuple[str, ...] = meta and getattr(meta, "form_exclude", ()) or ()
        return cls.make_pydantic(
            name="form",
            exclude=(
                *form_exclude,
                *(
                    ["created_at", "updated_at"]
                    if required_override is None
                    else ["created_at"]
                ),
                *([] if from_models else ["id"]),
            ),
            required_override=required_override,
            from_models=from_models,
            is_form=True,
        )

    @classmethod
    def make_pydantic(
        cls,
        name: str,
        include: Optional[Tuple[str, ...]] = None,
        exclude: Optional[Tuple[str, ...]] = None,
        required_override: Optional[bool] = None,
        from_models: Tuple[str, ...] = (),
        max_recursion: Optional[int] = None,
        is_form: bool = False,
    ):
        parts = [cls.__module__, cls.__qualname__, name]
        if from_models:
            parts.append("in")
            parts += from_models
        if required_override is not None:
            parts.append("required" if required_override else "optional")

        meta = cls.FormPydanticMeta if is_form else cls.PydanticMeta
        in_max_recursion = getattr(meta, "max_recursion", 0)
        return patch_pydantic(
            pydantic_model_creator(
                cls,
                name=".".join(parts),
                include=include or (),
                exclude=exclude or (),
                meta_override=meta,
            ),
            from_models=(*from_models, cls.__qualname__),
            required_override=required_override,
            is_form=is_form,
            max_recursion=max_recursion or in_max_recursion,
        )

    @classmethod
    def process(cls, input: Any):
        dic: Dict[str, Any] = (
            input if isinstance(input, dict) else input.dict(exclude_unset=True)
        )

        # 处理计算量
        computed: Dict[str, Any] = {}
        for field in cls.FormPydanticMeta.computed:
            if field not in dic:
                continue
            computed[field] = dic.pop(field)

        # 处理 m2m
        m2ms: Dict[str, Any] = {}
        for m2m_field in cls._meta.m2m_fields:
            values = dic.pop(m2m_field, None)
            if values is None:
                continue
            m2ms[m2m_field] = values

        return dic, computed, m2ms

    async def update_computed(self, computed: Dict[str, Any]):
        # 处理计算量
        for field, v in computed.items():
            setter = getattr(self, f"set_{field}", None)
            if setter is None:
                continue
            if inspect.iscoroutinefunction(setter):
                await setter(v)
            else:
                setter(v)

    async def update(self, input: Any):
        dic, computed, m2ms = self.process(input)

        # 处理计算量
        await self.update_computed(computed)
        self.update_from_dict(dic)  # type: ignore
        await self.save_m2ms(m2ms)

    async def save_m2ms(self, m2ms: Dict[str, Any]):
        if len(m2ms) == 0:
            return

        fields_map = self.fields_map()
        for m2m_field_name, values in m2ms.items():
            m2m_field = fields_map[m2m_field_name]
            if not isinstance(m2m_field, ManyToManyFieldInstance):
                continue
            model = m2m_field.related_model
            m2m = getattr(self, m2m_field_name)
            await m2m.clear()
            for raw in values:
                value_id = raw.get("id")
                if value_id:
                    value = await model.get(id=value_id)
                else:
                    value = await model.create(**raw)
                await m2m.add(value)

    async def fetch_related(
        self, *args: Any, using_db: Optional[BaseDBAsyncClient] = None
    ) -> None:
        meta: Optional[PydanticMeta] = getattr(self.__class__, "PydanticMeta", None)
        computed: Set[str]
        if meta and hasattr(meta, "computed"):
            computed = set(meta.computed)
            for field in args:
                if field in computed:
                    f = getattr(self, field, None)
                    if not f:
                        continue
                    if inspect.iscoroutinefunction(f):
                        setattr(self, field, await f())
        else:
            computed = set()

        normlized_args = [
            self.normalize_field(field) if isinstance(field, str) else field
            for field in args
            if field not in computed
        ]
        return await super().fetch_related(*normlized_args, using_db=using_db)

    async def fetch_related_lazy(
        self, path: str, using_db: Optional[BaseDBAsyncClient] = None
    ) -> Optional[Any]:
        instance = getattr(self, path)
        if isinstance(instance, Model):
            return instance

        await self.fetch_related(path, using_db=using_db)
        return getattr(self, path)

    @staticmethod
    def normalize_field(field: str) -> str:
        return field.replace(".", "__")

    @classmethod
    @lru_cache
    def get_model(cls, model_name: str) -> Optional[Type[Model]]:
        parts: List[str] = model_name.split(".")
        if len(parts) == 1:
            for app in Tortoise.apps:
                m = cls.get_model(f"{app}.{model_name}")
                if m:
                    return m
        return cast(
            Optional[Type[BaseModel]],
            Tortoise.apps.get(parts[0], {}).get(parts[1], None),
        )

    @classmethod
    @lru_cache
    def get_field(
        cls, model_name: str, field_name: str
    ) -> Tuple[Optional[Type[Model]], Optional[Field[Any]]]:
        model = cls.get_model(model_name)
        if model:
            model_meta = getattr(model, "_meta")
            fields_map: Dict[str, Field[Any]] = (
                getattr(model_meta, "fields_map") if model_meta else {}
            )
            field = fields_map.get(field_name)
            return model, field
        else:
            return model, None

    @classmethod
    @lru_cache
    def get_field_model(cls, field: str) -> Type[Model]:
        fields_map = cls.fields_map()
        fk_field = fields_map[field]
        model_name = getattr(fk_field, "model_name")
        model = cls.get_model(model_name)
        assert model
        return model


class BaseUpdateModel(BaseModel):
    updated_at: datetime = LocalDatetimeField(null=False, auto_now=True, index=True)

    class Meta:
        abstract = True
