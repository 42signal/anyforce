from typing import Any, Callable, Coroutine, Union

from fastapi import Depends

from ..g import set_user


def with_context(get_current_user: Callable[..., Union[Coroutine[Any, Any, Any], Any]]):
    async def f(current_user: Any = Depends(get_current_user)):
        set_user(current_user)
        return current_user

    return f
