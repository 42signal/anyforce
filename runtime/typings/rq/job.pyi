from typing import Any, Dict, List, Optional, Union

class Retry:
    def __init__(self, max: int, interval: Union[int, List[int]] = ...) -> None: ...

class Job:
    id: str
    args: List[Any]
    kwargs: Dict[str, Any]
    is_finished: bool
    is_failed: bool
    is_canceled: bool
    is_stopped: bool
    result: Any
    @classmethod
    def fetch(
        cls, id: str, connection: Any, serializer: Optional[Any] = ...
    ) -> Job: ...
    @classmethod
    def fetch_many(
        cls, job_ids: List[str], connection: Any, serializer: Optional[Any] = ...
    ) -> List[Job]: ...
    def cancel(self) -> None: ...
