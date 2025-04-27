from datetime import datetime, timedelta
from typing import Any, Callable, Type

from rq.job import Retry
from rq.registry import BaseRegistry

class Queue:
    name: str
    connection: Any
    serializer: Any
    scheduled_job_registry: BaseRegistry
    started_job_registry: BaseRegistry
    finished_job_registry: BaseRegistry
    failed_job_registry: BaseRegistry
    def __init__(
        self,
        name: str = ...,
        default_timeout: int = ...,
        connection: Any = ...,
        is_async: bool = ...,
        job_class: Type[Any] = ...,
        serializer: Any = ...,
        **kwargs: Any,
    ) -> None: ...
    def enqueue(
        self,
        f: Callable[..., Any],
        *args: Any,
        retry: Retry | None = ...,
        **kwargs: Any,
    ) -> Any: ...
    def enqueue_at(
        self,
        datetime: datetime,
        f: Callable[..., Any],
        *args: Any,
        retry: Retry | None = ...,
        **kwargs: Any,
    ) -> Any: ...
    def enqueue_in(
        self,
        time_delta: timedelta,
        f: Callable[..., Any],
        *args: Any,
        retry: Retry | None = ...,
        **kwargs: Any,
    ) -> Any: ...
    def enqueue_many(self, job_datas: list[Any], pipeline: Any = ...) -> list[Any]: ...
