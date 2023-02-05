from __future__ import annotations

from typing import Any, Type, TypeVar

from aenum import EJECT
from aenum import IntEnum as aIntEnum
from aenum import StrEnum as aStrEnum


class EnumMissingError(Exception):
    def __init__(self, enum_type: Any, value: Any, *args: Any) -> None:
        super().__init__(*args)
        self.enum_type = enum_type
        self.value = value


StrEnumT = TypeVar("StrEnumT", bound="StrEnum")


class StrEnum(aStrEnum):
    _init_ = "value __doc__"

    @classmethod
    def _missing_value_(cls, value: Any):
        raise EnumMissingError(cls, value, f"枚举值 {value} 不存在")

    @classmethod
    def t(cls: Type[StrEnumT], v: Any) -> StrEnumT:
        return v


IntEnumT = TypeVar("IntEnumT", bound="IntEnum")


class IntEnum(aIntEnum):
    _init_ = "value __doc__"

    @classmethod
    def _missing_value_(cls, value: Any):
        raise EnumMissingError(cls, value, f"枚举值 {value} 不存在")

    @classmethod
    def t(cls: Type[IntEnumT], v: Any) -> IntEnumT:
        return v


def eject(v: Any):
    return v


def allow_eject(enum: Any):
    enum._missing_value_ = eject
    enum._boundary_ = EJECT
