import inspect
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Tuple, Type, cast

from pydantic.fields import ComputedFieldInfo, FieldInfo
from pydantic_core import PydanticUndefined
from tortoise.contrib.pydantic.base import PydanticModel
from tortoise.exceptions import NoValuesFetched
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
from tortoise.queryset import AwaitableQuery


def patch_pydantic(
    cls: type[Model],
    model: Type[PydanticModel],
    from_models: Tuple[str, ...] = (),
    required_override: Optional[bool] = None,
    is_form: bool = False,
    max_recursion: int = 1,
) -> Type[PydanticModel]:
    model.model_config["extra"] = "ignore"

    # 解决数据动态加载的问题
    db_fields: Dict[str, Field[Any]] = cls._meta.fields_map  # type: ignore
    model_fields: Dict[str, FieldInfo] = {}
    for k, field in model.model_fields.items():
        db_field = db_fields.get(k)
        if not db_field:
            continue

        if required_override is False:
            field.annotation = Optional[field.annotation]  # type: ignore
            field.default = (
                None if field.default == PydanticUndefined else field.default
            )

        if db_field.default is not None:
            field.annotation = Optional[field.annotation]  # type: ignore
            field.default = None

        if isinstance(db_field, RelationalField):
            orig_model: Optional[Any] = getattr(db_field, "related_model", None)
            if orig_model:
                if len(from_models) > max_recursion:
                    continue

                if isinstance(db_field, BackwardFKRelation):
                    if is_form:
                        continue

                if isinstance(
                    db_field, (ForeignKeyFieldInstance, OneToOneFieldInstance)
                ):
                    is_required = (
                        field.is_required()
                        if required_override is None
                        else required_override
                    )
                    is_required = False if db_field.null else is_required

                    k_id = f"{k}_id"
                    k_type = int if is_required else Optional[int]
                    k_default = PydanticUndefined if is_required else None
                    model_fields[k_id] = FieldInfo(
                        annotation=k_type,
                        default=k_default,
                    )
                    if is_form:
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

                if isinstance(
                    db_field, (ForeignKeyFieldInstance, OneToOneFieldInstance)
                ):
                    field = FieldInfo(
                        annotation=Optional[field_pydantic_model],  # type: ignore
                        default=None,
                    )
                elif isinstance(
                    db_field, (BackwardFKRelation, ManyToManyFieldInstance)
                ):
                    field = FieldInfo(annotation=List[field_pydantic_model], default=[])

        model_fields[k] = field

    model_computed_fields: Dict[str, ComputedFieldInfo] = {}
    for k, field in model.model_computed_fields.items():
        fget = field.wrapped_property.fget
        if inspect.iscoroutinefunction(fget):
            model_fields[k] = FieldInfo(
                annotation=Optional[field.return_type],  # type: ignore
                default=None,
            )
            if k in model.__pydantic_decorators__.computed_fields:
                del model.__pydantic_decorators__.computed_fields[k]
            continue

        model_computed_fields[k] = field

    model.model_fields = model_fields
    model.model_computed_fields = model_computed_fields
    model.model_rebuild(force=True)

    origin__init__ = model.__init__
    origin_model_validate = model.model_validate
    origin_model_dump = model.model_dump

    def to_field(
        k: Optional[str] = None, model: Optional[Type[PydanticModel]] = None
    ) -> Field[Any] | None:
        if not k or not model:
            return
        orig_model = getattr(model, "model_config", {}).get("orig_model")
        if not orig_model:
            return
        fields: Dict[str, Field[Any]] = orig_model._meta.fields_map  # type: ignore
        return fields.get(k)

    def to_model(field: FieldInfo) -> Type[PydanticModel] | None:
        _model: Type[PydanticModel] | None = None
        _args: Any | None = getattr(field.annotation, "__args__", None)
        while _args:
            if not isinstance(_args, tuple):
                break
            if isinstance(_args[0], type) and issubclass(_args[0], PydanticModel):
                _model = _args[0]
                break
            _args = getattr(cast(Any, _args[0]), "__args__", None)
        return _model

    def to_dict(
        v: Any,
        field: Optional[Field[Any]] = None,
        k: Optional[str] = None,
        model: Optional[Type[PydanticModel]] = None,
    ) -> Any | None:
        field = field or to_field(k, model)
        if (
            v is None
            and field is not None
            and not field.null
            and field.default is not None
        ):
            return PydanticUndefined

        if v == PydanticUndefined:
            return PydanticUndefined
        if (
            isinstance(v, AwaitableQuery)
            or inspect.iscoroutinefunction(v)
            or inspect.iscoroutine(v)
            or v is NoneAwaitable
        ):
            return PydanticUndefined
        if isinstance(v, ReverseRelation):
            try:
                v = cast(Any, v)
                v = list(v)
            except NoValuesFetched:
                return PydanticUndefined
        if isinstance(v, (list, tuple)):
            vs: list[Any] = []
            for vi in cast(Iterable[Any], v):
                vn = to_dict(vi, field, k, model)
                if vn != PydanticUndefined:
                    vs.append(vn)
            return vs
        if isinstance(v, PydanticModel):
            return v.model_dump()
        if isinstance(v, Model):
            vd: dict[str, Any] = {}

            db_fields: Dict[str, Field[Any]] = {}
            db_fields = v.__class__._meta.fields_map  # type: ignore
            for ki, field in db_fields.items():
                vi = getattr(v, ki, PydanticUndefined)
                vn = to_dict(vi, field)
                if vn != PydanticUndefined:
                    vd[ki] = vn

            computed_fields: Tuple[str, ...] = getattr(  # type: ignore
                getattr(v.__class__, "PydanticMeta", None), "computed", ()
            )
            for ki in computed_fields:
                fget = getattr(v, ki, PydanticUndefined)
                if fget == PydanticUndefined:
                    continue
                vn = to_dict(fget() if callable(fget) else fget)
                if vn != PydanticUndefined:
                    vd[ki] = vn
            return vd
        if model and not k:
            vd: dict[str, Any] = {}
            for ki, fi in model.model_fields.items():
                new_model = to_model(fi)
                vi: Any = (
                    cast(Dict[str, Any], v).get(ki, PydanticUndefined)
                    if isinstance(v, dict)
                    else getattr(v, ki, PydanticUndefined)
                )
                vn = (
                    to_dict(vi, None, None, new_model)
                    if new_model
                    else to_dict(vi, None, ki, model)
                )
                if vn != PydanticUndefined:
                    vd[ki] = vn
            return vd
        elif isinstance(v, dict):
            vd: dict[str, Any] = {}
            for ki, vi in cast(dict[str, Any], v).items():
                vn = to_dict(vi)
                if vn != PydanticUndefined:
                    vd[ki] = vn
            return vd

        return v

    def model_validate(
        cls: Type[PydanticModel],
        obj: Any,
        strict: bool | None = None,
        from_attributes: bool | None = False,
        context: Any | None = None,
    ) -> PydanticModel:
        dic = to_dict(obj, None, None, cls)
        return origin_model_validate(
            dic, strict=strict, from_attributes=from_attributes, context=context
        )

    def model_dump(self: PydanticModel, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        if kwargs.get("exclude_none") is not None:
            kwargs["exclude_none"] = True
        data = origin_model_dump(self, *args, **kwargs)
        return cast(dict[str, Any], to_dict(data, None, None, self.__class__))

    def __init__(self: PydanticModel, **data: Any) -> None:  # type: ignore
        dic = cast(dict[str, Any], to_dict(data, None, None, self.__class__))
        origin__init__(self, **dic)
        return

    model.model_validate = classmethod(model_validate)  # type: ignore
    model.model_dump = model_dump
    model.__init__ = __init__
    return model
