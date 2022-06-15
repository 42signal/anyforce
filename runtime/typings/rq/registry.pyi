from datetime import datetime
from typing import Any, List, Union

from .job import Job

class BaseRegistry:
    count: int
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def get_job_ids(self, start: int = ..., end: int = ...) -> List[str]: ...

class ScheduledJobRegistry(BaseRegistry):
    def get_scheduled_time(self, job_or_id: Union[Job, str]) -> datetime: ...
