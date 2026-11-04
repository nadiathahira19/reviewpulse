import uuid
from collections.abc import Iterator

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

import app.job_queue as job_queue_module
from app.job_queue import (
    QueueUnavailable,
    RqJobQueue,
    get_job_queue,
    get_redis_url,
)
from app.jobs import run_analyze_batch

REDIS_URL = "redis://localhost:6379/0"


class FakeRqQueue:
    """Stands in for rq.Queue, so no Redis is needed."""

    calls: list[tuple[object, tuple[object, ...], dict[str, object]]] = []
    fail: bool = False

    def __init__(self, name: str, connection: object) -> None:
        self.name = name
        self.connection = connection

    def enqueue(self, func: object, *args: object, **kwargs: object) -> None:
        if FakeRqQueue.fail:
            raise RedisConnectionError("no redis")
        FakeRqQueue.calls.append((func, args, kwargs))


@pytest.fixture(autouse=True)
def fake_rq(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    FakeRqQueue.calls = []
    FakeRqQueue.fail = False
    monkeypatch.setattr(job_queue_module, "Queue", FakeRqQueue)
    job_queue_module.build_job_queue.cache_clear()
    yield
    job_queue_module.build_job_queue.cache_clear()


def test_redis_url_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    assert get_redis_url() == REDIS_URL


def test_redis_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        get_redis_url()


def test_job_is_enqueued_with_text_arguments_and_a_timeout() -> None:
    tenant_id, batch_id = uuid.uuid4(), uuid.uuid4()
    RqJobQueue(REDIS_URL).enqueue_batch_analysis(tenant_id, batch_id)
    func, args, kwargs = FakeRqQueue.calls[0]
    assert func is run_analyze_batch
    assert args == (str(tenant_id), str(batch_id))
    assert kwargs == {"job_timeout": job_queue_module.JOB_TIMEOUT_SECONDS}


def test_a_redis_error_becomes_queue_unavailable() -> None:
    FakeRqQueue.fail = True
    with pytest.raises(QueueUnavailable):
        RqJobQueue(REDIS_URL).enqueue_batch_analysis(uuid.uuid4(), uuid.uuid4())


def test_dependency_refuses_with_503_when_redis_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(HTTPException) as error:
        get_job_queue()
    assert error.value.status_code == 503


def test_dependency_returns_one_queue_per_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    first = get_job_queue()
    assert isinstance(first, RqJobQueue)
    assert get_job_queue() is first
