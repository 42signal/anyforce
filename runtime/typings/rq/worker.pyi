from typing import Any, List, Type

from .queue import Queue

class Worker:
    def __init__(
        self,
        queues: List[Queue],
        name: str = ...,
        default_result_ttl: int = ...,
        connection: Any = ...,
        exc_handler: Any = ...,
        exception_handlers: Any = ...,
        default_worker_ttl: int = ...,
        job_class: Type[Any] = ...,
        queue_class: Type[Any] = ...,
        log_job_description: bool = ...,
        job_monitoring_interval: int = ...,
        disable_default_exception_handler: bool = ...,
        prepare_for_work: bool = ...,
        serializer: Any = ...,
    ) -> None: ...
    def work(
        self,
        burst: bool = ...,
        logging_level: str = ...,
        date_format: str = ...,
        log_format: str = ...,
        max_jobs: int = ...,
        with_scheduler: bool = ...,
    ) -> bool: ...
