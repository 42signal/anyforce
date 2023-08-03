from typing import Any, Dict

from tortoise import Tortoise
from tortoise.backends.base.client import BaseDBAsyncClient

from .base import BaseModel, BaseUpdateModel
from .enum import IntEnum, StrEnum
from .recoverable import RecoverableModel

connections: Dict[str, BaseDBAsyncClient] = {}


async def init(config: Dict[str, Any]):
    await Tortoise.init(config=config)  # type: ignore
    for k in config["apps"]:
        connections[k] = Tortoise.get_connection(k)


def init_models(config: Dict[str, Any]):
    for name, info in config["apps"].items():
        Tortoise.init_models(info["models"], name)


__all__ = [
    "StrEnum",
    "IntEnum",
    "BaseModel",
    "BaseUpdateModel",
    "RecoverableModel",
]
