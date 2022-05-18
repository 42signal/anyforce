import inspect
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple, Type, cast

from tortoise import Tortoise, fields
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.contrib.pydantic import PydanticModel, pydantic_model_creator
from tortoise.contrib.pydantic.creator import PydanticMeta
from tortoise.fields.relational import ManyToManyFieldInstance
from tortoise.models import Field, MetaInfo, Model

from .fields import LocalDatetimeField
from .patch import patch_pydantic


class BaseModel(Model):
    id: int = fields.IntField(pk=True)
    created_at: datetime = LocalDatetimeField(null=False, auto_now_add=True)
    updated_at: datetime = LocalDatetimeField(null=False, auto_now=True)

    class Meta:
        abstract = True

    # class PydanticMeta:
    #     max_levels = 1  # 最大模型层级
    #     computed: Tuple[str, ...] = ()  # 计算量, 异步计算量返回值需要标记为 Optional
    #     list_exclude: Tuple[str, ...] = ()  # 列表排除
    #     detail_include: Tuple[str, ...] = ()  # 详情叠加
    #     form_exclude: Tuple[str, ...] = ()  # 表单排除

    class FormPydanticMeta:
        computed = []

    async def dict(self, prefetch: Optional[List[str]] = None) -> Dict[str, Any]:
        if prefetch:
            await self.fetch_related(*prefetch)
        return self.detail().from_orm(self).dict()

    @classmethod
    @lru_cache
    def list(cls) -> Type[PydanticModel]:
        meta: Optional[PydanticMeta] = getattr(cls, "PydanticMeta", None)
        list_exclude: Tuple[str, ...] = meta and getattr(meta, "list_exclude", ()) or ()
        return cls.make_pydantic(
            name="list", exclude=list_exclude, required_override=False
        )

    @classmethod
    @lru_cache
    def detail(
        cls,
        required_override: Optional[bool] = None,
        from_models: Tuple[str, ...] = (),
        max_levels: Optional[int] = None,
    ) -> Type[PydanticModel]:
        meta: Optional[PydanticMeta] = getattr(cls, "PydanticMeta", None)
        detail_include: Tuple[str, ...] = (
            meta and getattr(meta, "detail_include", ()) or ()
        )
        return cls.make_pydantic(
            name="detail",
            include=detail_include,
            required_override=required_override,
            from_models=from_models,
            max_levels=max_levels,
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
        is_form: bool = False,
        max_levels: Optional[int] = None,
    ):
        parts = [cls.__module__, cls.__qualname__, name]
        if from_models:
            parts.append("in")
            parts += from_models
        if required_override is not None:
            parts.append("required" if required_override else "optional")

        meta: Optional[PydanticMeta] = getattr(cls, "PydanticMeta", None)
        if max_levels is None:
            max_levels = meta and getattr(meta, "max_levels", None)
            max_levels = max_levels if max_levels else 1
        return patch_pydantic(
            pydantic_model_creator(
                cls,
                name=".".join(parts),
                include=include or (),
                exclude=exclude or (),
                meta_override=cls.FormPydanticMeta if is_form else None,
            ),
            from_models=(*from_models, cls.__qualname__),
            required_override=required_override,
            is_form=is_form,
            max_levels=max_levels,
        )

    @classmethod
    def process(cls, input: Any):
        dic: Dict[str, Any] = (
            input if isinstance(input, dict) else input.dict(exclude_unset=True)
        )

        # 处理 m2m
        m2ms: Dict[str, Any] = {}
        for m2m_field in cls._meta.m2m_fields:
            values = dic.pop(m2m_field, None)
            if values is None:
                continue
            m2ms[m2m_field] = values

        return dic, m2ms

    async def update(self, input: Any):
        dic, m2ms = self.process(input)
        self.update_from_dict(dic)  # type: ignore
        await self.save_m2ms(m2ms)

    async def save_m2ms(self, m2ms: Dict[str, Any]):
        if len(m2ms) == 0:
            return

        for m2m_field, values in m2ms.items():
            model = cast(
                ManyToManyFieldInstance, self._meta.fields_map[m2m_field]
            ).related_model
            m2m = getattr(self, m2m_field)
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
    ) -> Tuple[Optional[Type[Model]], Optional[Field]]:
        model = cls.get_model(model_name)
        meta: Optional[MetaInfo] = model and getattr(model, "_meta")
        field = model and meta and meta.fields_map.get(field_name)
        return model, field

    @classmethod
    @lru_cache
    def get_field_model(cls, field: str) -> Type[Model]:
        meta: MetaInfo = getattr(cls, "_meta")
        fields_map = meta.fields_map
        fk_field = fields_map[field]
        model_name = getattr(fk_field, "model_name")
        model = cls.get_model(model_name)
        assert model
        return model
