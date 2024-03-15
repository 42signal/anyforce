from __future__ import annotations

from enum import IntEnum as StdlibIntEnum
from enum import StrEnum as StdlibStrEnum
from typing import Any, Callable, Optional, Tuple


class EnumMissingError(Exception):
    def __init__(self, enum_type: Any, value: Any, *args: Any) -> None:
        super().__init__(*args)
        self.enum_type = enum_type
        self.value = value

    @staticmethod
    def missing(enum_type: Any, value: Any):
        meta: Optional[Callable[[], Any]] = getattr(enum_type, "meta", None)
        label: str = getattr(meta(), "label", "") if meta else ""
        return EnumMissingError(enum_type, value, f"{label} 不存在枚举值 {value}")


class IntEnum(StdlibIntEnum):
    label: str
    args: Tuple[str, ...]

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
    args: Tuple[str, ...]

    def __new__(cls, value: str, label: str = "", *args: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.args = args
        return obj

    @classmethod
    def _missing_(cls, value: Any):
        raise EnumMissingError.missing(cls, value)
