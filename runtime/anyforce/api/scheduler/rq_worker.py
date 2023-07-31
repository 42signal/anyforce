from datetime import datetime, timedelta, timezone
from functools import reduce
from typing import Any, Callable, Dict, List, Optional

from rq import Queue
from rq.defaults import DEFAULT_RESULT_TTL
from rq.job import Job as RQJOb
from rq.registry import ScheduledJobRegistry

from .typing import Job
from .typing import JobStatus as Status
from .typing import Response
from .typing import Worker as WorkerProtocol


class Worker(object):
    def __init__(self, queue: Queue) -> None:
        super().__init__()
        self.queue = queue

    def _(self) -> WorkerProtocol:
        return self

    @property
    def registries(self):
        return [
            self.queue.scheduled_job_registry,
            self.queue.started_job_registry,
            self.queue.finished_job_registry,
            self.queue.failed_job_registry,
        ]

    async def explain(self, job: Job) -> Job:
        return job

    async def filter(self, condition: Optional[Dict[str, str]], job: Job):
        if not condition:
            return True
        for k, v in condition.items():
            if not v:
                continue
            if k == "status":
                if v != job.status:
                    return False
                continue
            vv = reduce(lambda c, ck: c.get(ck, {}), k.split("."), job.kwargs)
            if str(vv).find(v) < 0:
                return False
        return True

    def enqueue_at(
        self, datetime: datetime, f: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return self.queue.enqueue_at(datetime, f, *args, **kwargs)

    async def list(
        self, offset: int, limit: int, condition: Optional[Dict[str, str]] = None
    ) -> Response:
        jobs = await self.list_jobs(offset, limit, condition)
        return Response(
            data=jobs, total=sum([registry.count for registry in self.registries])
        )

    async def list_jobs(
        self, offset: int, limit: int, condition: Optional[Dict[str, str]]
    ):
        jobs: List[Job] = []
        for registry in self.registries:
            job_ids = registry.get_job_ids()
            for i in range(0, len(job_ids), limit):
                chunk_job_ids = job_ids[i : i + limit]
                rq_jobs: List[RQJOb] = RQJOb.fetch_many(
                    chunk_job_ids,
                    connection=self.queue.connection,
                    serializer=self.queue.serializer,
                )
                for job in rq_jobs:
                    status = Status.pending
                    if job.is_finished:
                        status = Status.finished
                    elif job.is_failed:
                        status = Status.failed
                    elif job.is_canceled or job.is_stopped:
                        status = Status.canceled

                    at = (
                        registry.get_expiration_time(job)
                        .replace(tzinfo=timezone.utc)
                        .astimezone()
                    )
                    if not isinstance(registry, ScheduledJobRegistry):
                        at -= timedelta(seconds=job.result_ttl or DEFAULT_RESULT_TTL)
                    translated_job = Job(
                        id=job.id,
                        at=at,
                        status=status,
                        meta=job.meta,
                        func=job.func,
                        args=job.args,
                        kwargs=job.kwargs,
                        exc_info=job.exc_info,
                        return_value=job.return_value(),
                    )
                    if not await self.filter(condition, translated_job):
                        continue

                    offset -= 1
                    if offset > 0:
                        continue

                    jobs.append(await self.explain(translated_job))
                    if len(jobs) >= limit:
                        return jobs

        return jobs

    def cancel(self, id: str) -> Any:
        rq_job = RQJOb.fetch(
            id, connection=self.queue.connection, serializer=self.queue.serializer
        )
        return rq_job.cancel()
