from typing import Any, Hashable

from starlette_context import context


def get(k: Hashable) -> Any:
    return context.data.get(k)  # type: ignore


def set(k: Hashable, v: Any):
    context.data[k] = v  # type: ignore


def user():
    return get("user")


def set_user(user: Any):
    return set("user", user)
