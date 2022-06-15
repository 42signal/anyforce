from typing import Any, Iterable, Optional

class CryptContext(object):
    def __init__(self, schemes: Optional[Iterable[str]] = ...) -> None: ...
    def verify(
        self,
        secret: str,
        hash: str,
        scheme: Optional[str] = ...,
        category: Optional[str] = ...,
        **kwds: Any,
    ) -> bool: ...
    def hash(
        self,
        secret: str,
        scheme: Optional[str] = ...,
        category: Optional[str] = ...,
        **kwds: Any,
    ) -> str: ...
