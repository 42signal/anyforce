from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Protocol,
    TypeVar,
)

from pydantic import BaseModel, Field

from ...model.enum import StrEnum

T = TypeVar("T")


def formatter(label: str, formatter: Callable[..., list[tuple[str, Any]]]):
    def wrapper(f: Callable[..., T]) -> Callable[..., T]:
        setattr(f, "label", label)
        setattr(f, "formatter", formatter)
        return f

    return wrapper


class JobStatus(StrEnum):
    pending = "pending", "等待"
    failed = "failed", "失败"
    finished = "finished", "完成"
    canceled = "canceled", "取消"


class Job(BaseModel):
    id: str
    at: datetime
    status: JobStatus = JobStatus.pending
    func: Callable[..., Any] | None = Field(None, exclude=True)
    meta: dict[str, Any] = Field(default_factory=dict)
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    explain_func: str = ""
    explain_lines: list[tuple[str, list[tuple[str, Any]]]] = Field(
        default_factory=list[tuple[str, list[tuple[str, Any]]]]
    )
    exc_info: str | None = None
    return_value: Any | None = None


class Response(BaseModel):
    total: int
    data: list[Job]


class Worker(Protocol):
    def enqueue_at(
        self, datetime: datetime, f: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        raise NotImplementedError()

    def list(
        self, offset: int, limit: int, condition: dict[str, str] | None
    ) -> Awaitable[Response]:
        raise NotImplementedError()

    def cancel(self, id: str) -> Any:
        raise NotImplementedError()
