from typing import Any, Callable

class Retry:
    def __init__(self, max: int, interval: int | list[int] = ...) -> None: ...

class Job:
    id: str
    meta: dict[str, Any]
    func: Callable[..., Any] | None
    args: list[Any]
    kwargs: dict[str, Any]
    result_ttl: int | None
    ttl: int | None
    is_finished: bool
    is_failed: bool
    is_canceled: bool
    is_stopped: bool
    exc_info: str | None
    def return_value(self) -> Any | None: ...
    @classmethod
    def fetch(
        cls, id: str, connection: Any, serializer: Any | None = ...
    ) -> Job: ...
    @classmethod
    def fetch_many(
        cls, job_ids: list[str], connection: Any, serializer: Any | None = ...
    ) -> list[Job]: ...
    def cancel(self) -> None: ...
