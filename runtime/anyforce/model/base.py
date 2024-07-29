import inspect
from datetime import datetime
from functools import lru_cache
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel as PydanticModel
from pydantic import ConfigDict, create_model
from pydantic.fields import FieldInfo
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import BeforeValidator
from pydantic_core import PydanticUndefined
from tortoise import Tortoise
from tortoise import fields as tortoise_fields
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.fields.base import Field
from tortoise.fields.relational import (
    BackwardFKRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    NoneAwaitable,
    OneToOneFieldInstance,
    RelationalField,
    ReverseRelation,
)
from tortoise.models import Model
from tortoise.queryset import QuerySet

from .fields import (
    CurrencyDBField,
    IntField,
    LocalDatetimeField,
    SplitCharDBField,
)


class BaseModel(Model):
    id: int = IntField(primary_key=True)
    created_at: datetime = LocalDatetimeField(
        null=False, auto_now_add=True, db_index=True
    )

    class Meta(Model.Meta):
        abstract = True

    class PydanticMeta:
        config: ConfigDict = ConfigDict(
            from_attributes=True, arbitrary_types_allowed=True
        )
        validators: Optional[Dict[str, Callable[..., Any]]] = None
        include: Tuple[str, ...] = tuple()
        exclude: Tuple[str, ...] = tuple()
        computed: Tuple[str, ...] = tuple()  # 计算量
        form_exclude: Tuple[str, ...] = tuple()  # 表单排除
        list_exclude: Tuple[str, ...] = tuple()  # 列表排除
        max_recursion = 1

    class FormPydanticMeta(PydanticMeta):
        computed: Tuple[str, ...] = tuple()  # set_{property} 函数

    def dict(
        self,
        mode: Literal["json", "python"] = "python",
        include: Optional[Union[Set[int], Set[str]]] = None,
        exclude: Optional[Union[Set[int], Set[str]]] = None,
        context: Optional[Any] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: Union[bool, Literal["none", "warn", "error"]] = True,
        serialize_as_any: bool = False,
    ) -> Dict[str, Any]:
        return (
            self.detail()
            .model_validate(self)
            .model_dump(
                mode=mode,
                include=include,
                exclude=exclude,
                context=context,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                round_trip=round_trip,
                warnings=warnings,
                serialize_as_any=serialize_as_any,
            )
        )

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
            name="list", required_override=False, exclude=cls.PydanticMeta.list_exclude
        )

    @classmethod
    @lru_cache
    def detail(
        cls,
        required_override: Optional[bool] = False,
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
        meta = cls.PydanticMeta
        form_exclude: Tuple[str, ...] = meta.form_exclude
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
        max_recursion = max_recursion if max_recursion else meta.max_recursion

        from_models = (*from_models, cls.__qualname__)
        include = include if include is not None else meta.include
        exclude = exclude if exclude is not None else meta.exclude

        fields: Dict[str, Any] = {}

        # 处理数据库字段
        for name, field in cls.fields_map().items():
            if include and name not in include:
                continue
            if exclude and name in exclude:
                continue

            if isinstance(field, RelationalField):
                if len(from_models) > max_recursion:
                    continue

                orig_model: Optional[Type[Model]] = getattr(
                    field, "related_model", None
                )
                assert orig_model

                if isinstance(field, BackwardFKRelation) and is_form:
                    continue

                if isinstance(field, (ForeignKeyFieldInstance, OneToOneFieldInstance)):
                    fields[f"{name}_id"] = (
                        int if field.null else Optional[int],
                        FieldInfo(
                            default=(
                                None
                                if field.null
                                else (
                                    PydanticUndefined
                                    if field.default is None
                                    else field.default
                                )
                            )
                        ),
                    )
                    if is_form:
                        continue

                if not issubclass(orig_model, BaseModel):
                    continue

                if is_form:
                    field_pydantic_model = orig_model.form(
                        from_models=from_models,
                        required_override=False,
                    )
                else:
                    field_pydantic_model = orig_model.detail(
                        from_models=from_models,
                        required_override=required_override is True,
                    )

                if isinstance(field, (ForeignKeyFieldInstance, OneToOneFieldInstance)):
                    fields[name] = (
                        Annotated[
                            Optional[field_pydantic_model],
                            BeforeValidator(BaseModel.validate_relation),
                        ],
                        FieldInfo(title=field.description, default=None),
                    )
                elif isinstance(
                    field,
                    (BackwardFKRelation, ManyToManyFieldInstance, ReverseRelation),
                ):
                    fields[name] = (
                        Annotated[
                            Optional[List[field_pydantic_model]],
                            BeforeValidator(BaseModel.validate_relations),
                        ],
                        FieldInfo(title=field.description, default=None),
                    )

                continue

            field_default = field.default
            if required_override is True:
                field_default = PydanticUndefined
            elif required_override is False:
                field_default = field.default
            elif field_default is None:
                if field.null:
                    field_default = None
                elif isinstance(
                    field, (tortoise_fields.DatetimeField, tortoise_fields.TimeField)
                ):
                    field_default = (
                        datetime.now
                        if (field.auto_now or field.auto_now_add)
                        else PydanticUndefined
                    )
                else:
                    field_default = PydanticUndefined

            f_kwargs: dict[str, Any] = {}
            if isinstance(field, SplitCharDBField):
                type_hint = List[str]
            elif isinstance(field, (CurrencyDBField, tortoise_fields.DecimalField)):
                type_hint = float
            else:
                type_hint = field.field_type
                if (
                    isinstance(field, tortoise_fields.CharField)
                    and field.max_length > 0
                ):
                    f_kwargs["max_length"] = field.max_length

            if not field.field_type:
                type_hint = get_type_hints(field.to_python_value).get("return", Any)
                if not field.null and get_origin(type_hint) == Union:
                    args = getattr(type_hint, "__args__")
                    if len(args) == 2 and args[1] is None:
                        type_hint = args[0]

            if field.null or required_override is False:
                is_optional = get_origin(type_hint) == Union
                if is_optional:
                    args = getattr(type_hint, "__args__")
                    is_optional = len(args) == 2 and args[1] is None
                if not is_optional:
                    type_hint = Optional[type_hint]

            fields[name] = (
                type_hint,
                FieldInfo(
                    default=(
                        PydanticUndefined if callable(field_default) else field_default
                    ),
                    default_factory=field_default if callable(field_default) else None,
                    description=field.description,
                    **f_kwargs,
                ),
            )

        # 处理计算字段
        for name in meta.computed:
            if include and name not in include:
                continue
            if exclude and name in exclude:
                continue

            f = getattr(cls, name, None)
            if not f or not callable(f):
                continue

            return_type = get_type_hints(f).get("return", Any)
            is_optional = get_origin(return_type) == Union
            if is_optional:
                args = getattr(return_type, "__args__")
                is_optional = len(args) == 2 and args[1] is None
            if not is_optional:
                return_type = Optional[return_type]

            fields[name] = (
                Annotated[
                    return_type,
                    BeforeValidator(BaseModel.validate_computed),
                    PlainSerializer(BaseModel.serialize_computed),
                ],
                FieldInfo(
                    description=inspect.cleandoc(f.__doc__ or ""),
                    default=None,
                ),
            )

        return create_model(
            ".".join(parts),
            __config__=meta.config,
            __validators__=meta.validators,
            **fields,
        )

    @staticmethod
    def validate_computed(v: Any):
        if callable(v):
            return None
        return v

    @staticmethod
    def serialize_computed(v: Any):
        if isinstance(v, BaseModel):
            v = v.list().model_validate(v)
        elif isinstance(v, list):
            v = [
                (e.list().model_validate(e) if isinstance(e, BaseModel) else e)
                for e in cast(List[Any], v)
            ]
        return v

    @staticmethod
    def validate_relation(v: Any):
        if hasattr(v, "_fetched") and not getattr(v, "_fetched"):
            return None
        if isinstance(v, (QuerySet, NoneAwaitable.__class__)):
            return None
        return v

    @staticmethod
    def validate_relations(v: Any):
        if hasattr(v, "_fetched"):
            if getattr(v, "_fetched"):
                return list(v)
            return None
        else:
            return v

    @classmethod
    def process(cls, input: Any):
        dic: Dict[str, Any] = (
            input if isinstance(input, dict) else input.model_dump(exclude_unset=True)
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
        meta = self.PydanticMeta
        computed: Set[str]
        if meta and hasattr(meta, "computed"):
            computed = set(meta.computed)
            for field in args:
                if field in computed:
                    f = getattr(self, field, None)
                    if not f:
                        continue
                    if callable(f):
                        v = f()
                        if inspect.isawaitable(v):
                            v = await v
                        setattr(self, field, v)
        else:
            computed = set()

        normalized_args = [
            self.normalize_field(field) if isinstance(field, str) else field
            for field in args
            if field not in computed
        ]
        return await super().fetch_related(*normalized_args, using_db=using_db)

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
            return None
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
    updated_at: datetime = LocalDatetimeField(null=False, auto_now=True, db_index=True)

    class Meta(BaseModel.Meta):
        abstract = True
