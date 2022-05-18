from typing import Any, Callable, Coroutine, Union

from fastapi import Depends
from passlib.context import CryptContext

from ..g import set_user

password_context: CryptContext = CryptContext(schemes=["bcrypt"])


def with_context(get_current_user: Callable[..., Union[Coroutine[Any, Any, Any], Any]]):
    async def f(current_user: Any = Depends(get_current_user)):
        set_user(current_user)
        return current_user

    return f
