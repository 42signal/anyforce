from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from rq import Queue, Retry
from rq.job import Job as RQJOb

from .typing import Job
from .typing import JobStatus as Status
from .typing import Response
from .typing import Worker as WorkerProtocol


class Worker(object):
    def __init__(self, queue: Queue, retry: Optional[Retry] = None) -> None:
        super().__init__()
        self.queue = queue
        self.retry = retry

    def _(self) -> WorkerProtocol:
        return self

    @property
    def registry(self):
        return self.queue.scheduled_job_registry

    def enqueue_at(
        self, datetime: datetime, f: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return self.queue.enqueue_at(datetime, f, *args, retry=self.retry, **kwargs)

    def list(
        self, offset: int, limit: int, condition: Optional[Dict[str, str]] = None
    ) -> Response:
        jobs = self.list_jobs(offset, limit, condition)
        return Response(data=jobs, total=self.registry.count)

    def list_jobs(self, offset: int, limit: int, condition: Optional[Dict[str, str]]):
        jobs: List[Job] = []
        while True:
            job_ids = self.registry.get_job_ids(-(offset + limit), limit)
            offset += limit

            rq_jobs: List[RQJOb] = RQJOb.fetch_many(
                job_ids,
                connection=self.queue.connection,
                serializer=self.queue.serializer,
            )
            for job in rq_jobs:
                kwargs = job.kwargs.copy()
                context: Dict[str, str] = kwargs.pop("context", {})
                if condition:
                    matched = True
                    for k, v in condition.items():
                        if not v:
                            continue
                        if context.get(k, "").find(v) < 0:
                            matched = False
                            break
                    if not matched:
                        continue

                status = Status.pending
                if job.is_finished:
                    status = Status.finished
                elif job.is_failed:
                    status = Status.failed
                elif job.is_canceled or job.is_stopped:
                    status = Status.canceled

                jobs.append(
                    Job(
                        id=job.id,
                        at=self.registry.get_scheduled_time(job.id),
                        status=status,
                        args=job.args,
                        kwargs=kwargs,
                        context=context,
                        result=str(job.result) if job.result else "",
                    )
                )
                if len(jobs) >= limit:
                    return jobs

            if len(job_ids) < limit:
                return jobs

    def cancel(self, id: str) -> Any:
        rq_job = RQJOb.fetch(
            id, connection=self.queue.connection, serializer=self.queue.serializer
        )
        return rq_job.cancel()
