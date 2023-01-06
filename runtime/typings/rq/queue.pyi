from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional, Type

from rq.job import Retry
from rq.registry import ScheduledJobRegistry

class Queue:
    name: str
    connection: Any
    serializer: Any
    scheduled_job_registry: ScheduledJobRegistry
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
        retry: Optional[Retry] = ...,
        **kwargs: Any,
    ) -> Any: ...
    def enqueue_at(
        self,
        datetime: datetime,
        f: Callable[..., Any],
        *args: Any,
        retry: Optional[Retry] = ...,
        **kwargs: Any,
    ) -> Any: ...
    def enqueue_in(
        self,
        time_delta: timedelta,
        f: Callable[..., Any],
        *args: Any,
        retry: Optional[Retry] = ...,
        **kwargs: Any,
    ) -> Any: ...
    def enqueue_many(self, job_datas: List[Any], pipeline: Any = ...) -> List[Any]: ...
