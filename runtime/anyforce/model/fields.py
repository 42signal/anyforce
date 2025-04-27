import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import (
    Any,
    Awaitable,
    Literal,
    Type,
    cast,
)

from pypika_tortoise import functions
from pypika_tortoise.enums import SqlTypes
from pypika_tortoise.terms import Term
from tortoise import fields
from tortoise.fields import DatetimeField, relational
from tortoise.fields.base import OnDelete
from tortoise.fields.data import (
    DatetimeFieldQueryValueType,
    JsonDumpsFunc,
    JsonLoadsFunc,
)
from tortoise.models import Model

from ..json import fast_dumps
from ..json import loads as json_loads


def SmallIntField(
    source_field: str | None = None,
    primary_key: bool = False,
    null: bool = False,
    default: Any = None,
    unique: bool = False,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        int | fields.IntField,
        fields.SmallIntField(
            source_field=source_field,
            primary_key=primary_key,
            null=null,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


def IntField(
    source_field: str | None = None,
    primary_key: bool = False,
    null: bool = False,
    default: Any = None,
    unique: bool = False,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        int | fields.IntField,
        fields.IntField(
            source_field=source_field,
            primary_key=primary_key,
            null=null,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


def BigIntField(
    source_field: str | None = None,
    primary_key: bool = False,
    null: bool = False,
    default: Any = None,
    unique: bool = False,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        int | fields.BigIntField,
        fields.BigIntField(
            source_field=source_field,
            primary_key=primary_key,
            null=null,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


BooleanField = fields.BooleanField


def FloatField(
    source_field: str | None = None,
    null: bool = False,
    default: Any = None,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        float | fields.FloatField,
        fields.FloatField(
            source_field=source_field,
            null=null,
            default=default,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


def DecimalField(
    max_digits: int,
    decimal_places: int,
    source_field: str | None = None,
    null: bool = False,
    default: Any = None,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        Decimal | fields.DecimalField,
        fields.DecimalField(
            max_digits=max_digits,
            decimal_places=decimal_places,
            source_field=source_field,
            null=null,
            default=default,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


IntEnumField = fields.IntEnumField
CharEnumField = fields.CharEnumField


def DateField(
    source_field: str | None = None,
    null: bool = False,
    default: Any = None,
    unique: bool = False,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        date | fields.DateField,
        fields.DateField(
            source_field=source_field,
            null=null,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


TimeDeltaField = fields.TimeDeltaField
UUIDField = fields.UUIDField
BinaryField = fields.BinaryField

BackwardFKRelation = fields.BackwardFKRelation
ReverseRelation = fields.ReverseRelation
ManyToManyRelation = relational.ManyToManyRelation


def TextField(
    source_field: str | None = None,
    default: Any = None,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        str | fields.TextField,
        fields.TextField(
            source_field=source_field,
            default=default,
            description=description,
            **kwargs,
        ),
    )


class _LocalDatetimeField(DatetimeField):
    def to_db_value(
        self,
        value: DatetimeFieldQueryValueType | None,
        instance: Type[Model] | Model,
    ) -> DatetimeFieldQueryValueType | None:
        value = super().to_db_value(value, instance)
        if (
            value
            and isinstance(value, datetime)
            and value.tzinfo is not None
            and value.tzinfo.utcoffset(value) is not None
        ):
            value = value.astimezone()
        return value


def LocalDatetimeField(
    auto_now: bool = False,
    auto_now_add: bool = False,
    source_field: str | None = None,
    null: bool = False,
    default: Any = None,
    unique: bool = False,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        DatetimeField | datetime,
        _LocalDatetimeField(
            auto_now=auto_now,
            auto_now_add=auto_now_add,
            source_field=source_field,
            null=null,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


class TimeField(fields.TimeField):
    def to_python_value(self, value: Any):
        value = super().to_python_value(value)
        if isinstance(value, timedelta):
            value = (datetime.min + value).time()
        return value


def JSONField(
    source_field: str | None = None,
    default: Any = None,
    description: str | None = None,
    encoder: JsonDumpsFunc = fast_dumps,
    decoder: JsonLoadsFunc = json_loads,
    **kwargs: Any,
):
    return cast(
        dict[str, Any],
        fields.JSONField(
            source_field=source_field,
            default=default,
            description=description,
            encoder=encoder,
            decoder=decoder,
            **kwargs,
        ),
    )


def JSONListField(
    source_field: str | None = None,
    default: Any = None,
    description: str | None = None,
    encoder: JsonDumpsFunc = fast_dumps,
    decoder: JsonLoadsFunc = json_loads,
    **kwargs: Any,
):
    return cast(
        list[Any],
        fields.JSONField(
            source_field=source_field,
            default=default,
            description=description,
            encoder=encoder,
            decoder=decoder,
            **kwargs,
        ),
    )


class NullableCharField(fields.CharField):
    def __init__(
        self,
        max_length: int,
        source_field: str | None = None,
        primary_key: bool = False,
        default: Any = None,
        unique: bool = False,
        db_index: bool = False,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            max_length,
            null=True,
            source_field=source_field,
            primary_key=primary_key,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        )

    def to_python_value(self, value: str | None) -> list[str] | None:
        if value == "":
            value = None
        return super().to_python_value(value)

    def to_db_value(
        self, value: str | None, instance: Type[Model] | Model
    ) -> str | None:
        if value == "":
            value = None
        return super().to_db_value(value, instance)


class SplitCharDBField(fields.CharField, list[str]):
    def __init__(
        self,
        max_length: int,
        separator: str | None = None,
        default: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.separator = separator or "\n"
        super().__init__(max_length, default=default, **kwargs)

    def to_python_value(self, value: str | list[str] | None) -> list[str] | None:
        if value is None:
            return None

        if isinstance(value, list):
            return value

        v: str = super().to_python_value(value)
        if not v:
            return []
        return v.split(self.separator)

    def to_db_value(
        self, value: list[str] | None, instance: Type[Model] | Model
    ) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            return value

        return super().to_db_value(
            self.separator.join(value) if value else "", instance
        )

    def __bool__(self):
        return True


def SplitCharField(
    max_length: int,
    source_field: str | None = None,
    null: bool = False,
    default: list[str] | None = None,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        list[str],
        SplitCharDBField(
            max_length=max_length,
            source_field=source_field,
            null=null,
            default=default,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


class CurrencyDBField(fields.Field[int], float):
    SQL_TYPE = "BIGINT"
    allows_generated = True

    class _db_postgres:
        GENERATED_SQL = "BIGSERIAL NOT NULL PRIMARY KEY"

    class _db_sqlite:
        GENERATED_SQL = "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"

    class _db_mysql:
        GENERATED_SQL = "BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT"

    class _db_mssql:
        GENERATED_SQL = "BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY"

    class _db_oracle:
        SQL_TYPE = "INT"
        GENERATED_SQL = "INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY NOT NULL"

    @property
    def constraints(self):
        return {
            "ge": (
                1
                if self.generated or getattr(self, "reference")
                else -9223372036854775808
            ),
            "le": 9223372036854775807,
        }

    def __init__(
        self, primary_key: bool = False, multiply: float = 100.0, **kwargs: Any
    ) -> None:
        if primary_key:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(primary_key=primary_key, **kwargs)  # type: ignore
        self.multiply = multiply

    def to_python_value(self, value: int | float | None) -> float | None:
        if value is None:
            return None

        if isinstance(value, float):
            return value

        return float(value) / self.multiply

    def to_db_value(
        self, value: float | None, instance: Type[Model] | Model
    ) -> int | None:
        if value is None:
            return None
        return round(value * self.multiply)


def CurrencyField(
    source_field: str | None = None,
    null: bool = False,
    default: Any = None,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        float,
        CurrencyDBField(
            source_field=source_field,
            null=null,
            default=default,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


class CurrencyDecimalField(fields.Field[float], float):
    """
    存储为单位为分，支持小数
    """

    def __init__(
        self,
        primary_key: bool = False,
        multiply: float = 100.0,
        decimal_places: int = 1,
        max_digits: int = 12,
        **kwargs: Any,
    ) -> None:
        if primary_key:
            kwargs["generated"] = bool(kwargs.get("generated", True))

        self.multiply = multiply
        self.decimal_places = decimal_places
        self.max_digits = max_digits
        self.precision = self.decimal_places + int(round(math.log(self.multiply, 10)))

        super().__init__(primary_key=primary_key, **kwargs)  # type: ignore

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        return f"DECIMAL({self.max_digits}, {self.decimal_places})"

    class _db_sqlite:
        SQL_TYPE = "VARCHAR(40)"

        def function_cast(self, term: Term) -> Term:
            return functions.Cast(term, SqlTypes.NUMERIC)

    def to_python_value(self, value: float | Decimal | None) -> float | None:
        if value is None:
            return None

        if isinstance(value, float):
            return value

        return float(round(value / Decimal(self.multiply), self.precision))

    def to_db_value(
        self, value: float | None, instance: Type[Model] | Model
    ) -> Decimal | None:
        if value is None:
            return None
        return Decimal(round(value * self.multiply, self.decimal_places))


def CharField(
    max_length: int,
    source_field: str | None = None,
    primary_key: bool = False,
    null: bool = False,
    default: Any = None,
    unique: bool = False,
    db_index: bool = False,
    description: str | None = None,
    **kwargs: Any,
):
    return cast(
        fields.CharField | str,
        fields.CharField(
            max_length=max_length,
            source_field=source_field,
            primary_key=primary_key,
            null=null,
            default=default,
            unique=unique,
            db_index=db_index,
            description=description,
            **kwargs,
        ),
    )


def ForeignKeyField(
    model_name: str,
    related_name: str | Literal[False] | None = None,
    on_delete: OnDelete = OnDelete.RESTRICT,
    db_constraint: bool = True,
    **kwargs: Any,
) -> Awaitable[Model] | Model:
    return fields.ForeignKeyField(  # type: ignore
        model_name=model_name,
        related_name=related_name,
        on_delete=on_delete,
        db_constraint=db_constraint,
        **kwargs,
    )


def ManyToManyField(
    model_name: str,
    through: str | None = None,
    forward_key: str | None = None,
    backward_key: str = "",
    related_name: str = "",
    on_delete: OnDelete = OnDelete.CASCADE,
    db_constraint: bool = True,
    **kwargs: Any,
) -> relational.ManyToManyRelation[Model]:
    return fields.ManyToManyField(
        model_name=model_name,
        through=through,
        forward_key=forward_key,
        backward_key=backward_key,
        related_name=related_name,
        on_delete=on_delete,
        db_constraint=db_constraint,
        **kwargs,
    )
