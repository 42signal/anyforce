from typing import Any, Callable, Dict, List, Optional, Union

class Retry:
    def __init__(self, max: int, interval: Union[int, List[int]] = ...) -> None: ...

class Job:
    id: str
    func: Optional[Callable[..., Any]]
    args: List[Any]
    kwargs: Dict[str, Any]
    is_finished: bool
    is_failed: bool
    is_canceled: bool
    is_stopped: bool
    exc_info: Optional[str]
    def return_value(self) -> Optional[Any]: ...
    @classmethod
    def fetch(
        cls, id: str, connection: Any, serializer: Optional[Any] = ...
    ) -> Job: ...
    @classmethod
    def fetch_many(
        cls, job_ids: List[str], connection: Any, serializer: Optional[Any] = ...
    ) -> List[Job]: ...
    def cancel(self) -> None: ...
