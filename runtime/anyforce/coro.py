import asyncio
from functools import wraps
from typing import Any, Callable

import uvloop


def run(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any):
        uvloop.install()
        return asyncio.run(f(*args, **kwargs))

    return wrapper
