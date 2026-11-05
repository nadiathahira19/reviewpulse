"""Job queue on Redis with RQ (see docs/adr/0002)."""

import os
import uuid
from functools import lru_cache
from typing import Protocol

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue, Retry

from app.jobs import run_analyze_batch

QUEUE_NAME = "reviews"
# A big batch on a CPU can take many minutes. This is a first guess.
# It is checked later in the benchmark task.
JOB_TIMEOUT_SECONDS = 1800
# A job that fails (for example Postgres is restarting) is tried again after
# 10 s, 30 s and 60 s. After the last try it stays in RQ's failed registry.
RETRY_MAX = 3
RETRY_INTERVALS_SECONDS = [10, 30, 60]


class QueueUnavailable(Exception):
    """Redis cannot be reached, so the job could not be queued."""


def get_redis_url() -> str:
    """Read the Redis address from the environment. It is never written in the code."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set")
    return redis_url


class JobQueue(Protocol):
    def enqueue_batch_analysis(self, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> None: ...


class RqJobQueue:
    def __init__(self, redis_url: str) -> None:
        self._queue = Queue(QUEUE_NAME, connection=Redis.from_url(redis_url))

    def enqueue_batch_analysis(self, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> None:
        """Put the analysis of a batch in the queue. Arguments are sent as text."""
        try:
            self._queue.enqueue(
                run_analyze_batch,
                str(tenant_id),
                str(batch_id),
                job_timeout=JOB_TIMEOUT_SECONDS,
                retry=Retry(max=RETRY_MAX, interval=RETRY_INTERVALS_SECONDS),
            )
        except RedisError as error:
            raise QueueUnavailable("Could not reach Redis") from error


@lru_cache
def build_job_queue(redis_url: str) -> RqJobQueue:
    """One queue (and one Redis connection pool) per process."""
    return RqJobQueue(redis_url)


def get_job_queue() -> JobQueue:
    """FastAPI dependency. Without REDIS_URL the upload is refused before anything is saved."""
    try:
        redis_url = get_redis_url()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Job queue is not configured") from error
    return build_job_queue(redis_url)
