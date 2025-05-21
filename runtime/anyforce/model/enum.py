from __future__ import annotations

from enum import IntEnum as StdlibIntEnum
from enum import StrEnum as StdlibStrEnum
from typing import Any, Callable, Type


class EnumMissingError(Exception):
    def __init__(self, enum_type: Any, value: Any, *args: Any) -> None:
        super().__init__(*args)
        self.enum_type = enum_type
        self.value = value

    @staticmethod
    def missing(enum_type: Type[Any], value: Any):
        meta: Callable[[], Any] | None = getattr(enum_type, "meta", None)
        title: str = getattr(meta(), "title", "") if meta else ""
        return EnumMissingError(
            enum_type, value, f"{title or {enum_type.__name__}} 不存在枚举值 {value}"
        )


class IntEnum(StdlibIntEnum):
    label: str
    args: tuple[str, ...]

    def __new__(cls, value: int, label: str = "", *args: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.args = args
        return obj

    @classmethod
    def _missing_(cls, value: Any):
        raise EnumMissingError.missing(cls, value)


class StrEnum(StdlibStrEnum):
    label: str
    args: tuple[str, ...]

    def __new__(cls, value: str, label: str = "", *args: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.args = args
        return obj

    @classmethod
    def _missing_(cls, value: Any):
        raise EnumMissingError.missing(cls, value)
