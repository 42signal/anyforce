from typing import Any

from tortoise import Tortoise

from .base import BaseModel, BaseUpdateModel
from .enum import IntEnum, StrEnum
from .recoverable import RecoverableModel


async def init(config: dict[str, Any]):
    await Tortoise.init(config=config)  # type: ignore
    for k in config["apps"]:
        Tortoise.get_connection(k)


def init_models(config: dict[str, Any]):
    for name, info in config["apps"].items():
        Tortoise.init_models(info["models"], name)


__all__ = [
    "StrEnum",
    "IntEnum",
    "BaseModel",
    "BaseUpdateModel",
    "RecoverableModel",
]
