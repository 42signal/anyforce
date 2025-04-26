from typing import Any, Iterable

class CryptContext(object):
    def __init__(self, schemes: Iterable[str] | None = ...) -> None: ...
    def verify(
        self,
        secret: str,
        hash: str,
        scheme: str | None = ...,
        category: str | None = ...,
        **kwds: Any,
    ) -> bool: ...
    def hash(
        self,
        secret: str,
        scheme: str | None = ...,
        category: str | None = ...,
        **kwds: Any,
    ) -> str: ...
