from datetime import datetime
from typing import Any, Awaitable, List, Literal, Optional, Type, Union

from tortoise import fields
from tortoise.fields import DatetimeField
from tortoise.fields.data import JsonDumpsFunc, JsonLoadsFunc
from tortoise.fields.relational import ManyToManyRelation
from tortoise.models import Model

from ..json import fast_dumps
from ..json import loads as json_loads


class LocalDatetimeField(DatetimeField):
    def to_db_value(
        self, value: Optional[datetime], instance: Union[Type[Model], Model]
    ) -> Optional[datetime]:
        value = super().to_db_value(value, instance)
        if (
            value
            and value.tzinfo is not None
            and value.tzinfo.utcoffset(value) is not None
        ):
            value = value.astimezone()
        return value


def JSONField(
    encoder: JsonDumpsFunc = fast_dumps,
    decoder: JsonLoadsFunc = json_loads,
    **kwargs: Any,
):
    return fields.JSONField(encoder=encoder, decoder=decoder, **kwargs)


class NullableCharField(fields.CharField):
    def __init__(self, max_length: int, **kwargs: Any) -> None:
        super().__init__(max_length, null=True, **kwargs)

    def to_python_value(self, value: Optional[str]) -> Optional[List[str]]:
        if value == "":
            value = None
        return super().to_python_value(value)

    def to_db_value(
        self, value: Optional[str], instance: Union[Type[Model], Model]
    ) -> Optional[str]:
        if value == "":
            value = None
        return super().to_db_value(value, instance)


class SplitCharField(fields.CharField, List[str]):
    def __init__(
        self, max_length: int, separator: Optional[str] = None, **kwargs: Any
    ) -> None:
        super().__init__(max_length, **kwargs)
        self.separator = separator

    def to_python_value(
        self, value: Optional[Union[str, List[str]]]
    ) -> Optional[List[str]]:
        if value is None:
            return None

        if isinstance(value, list):
            return value

        v: str = super().to_python_value(value)
        if not v:
            return []
        return v.split(self.separator)

    def to_db_value(
        self, value: Optional[List[str]], instance: Union[Type[Model], Model]
    ) -> Optional[str]:
        if value is None:
            return None

        if isinstance(value, str):
            return value

        return super().to_db_value(
            (self.separator or "\n").join(value) if value else "", instance
        )

    def __bool__(self):
        return True


class CurrencyField(fields.Field, float):

    SQL_TYPE = "BIGINT"
    allows_generated = True

    class _db_postgres:
        GENERATED_SQL = "BIGSERIAL NOT NULL PRIMARY KEY"

    class _db_sqlite:
        GENERATED_SQL = "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"

    class _db_mysql:
        GENERATED_SQL = "BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT"

    @property
    def constraints(self):
        return {
            "ge": 1 if self.generated or self.reference else -9223372036854775808,
            "le": 9223372036854775807,
        }

    def __init__(
        self, pk: bool = False, multiply: float = 100.0, **kwargs: Any
    ) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)  # type: ignore
        self.multiply = multiply

    def to_python_value(self, value: Optional[Union[int, float]]) -> Optional[float]:
        if value is None:
            return None

        if isinstance(value, float):
            return value

        return value / self.multiply

    def to_db_value(
        self, value: Optional[float], instance: Union[Type[Model], Model]
    ) -> Optional[int]:
        if value is None:
            return None
        return round(value * self.multiply)


def ForeignKeyField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: str = "CASCADE",
    db_constraint: bool = True,
    **kwargs: Any,
) -> Union[Awaitable[Model], Model]:
    return fields.ForeignKeyField(  # type: ignore
        model_name=model_name,
        related_name=related_name,
        on_delete=on_delete,
        db_constraint=db_constraint,
        **kwargs,
    )


def ManyToManyField(
    model_name: str,
    through: Optional[str] = None,
    forward_key: Optional[str] = None,
    backward_key: str = "",
    related_name: str = "",
    on_delete: str = fields.CASCADE,
    db_constraint: bool = True,
    **kwargs: Any,
) -> ManyToManyRelation[Model]:
    return fields.ManyToManyField(  # type: ignore
        model_name=model_name,
        through=through,
        forward_key=forward_key,
        backward_key=backward_key,
        related_name=related_name,
        on_delete=on_delete,
        db_constraint=db_constraint,
        **kwargs,
    )
