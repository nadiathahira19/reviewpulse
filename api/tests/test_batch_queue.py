import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.job_queue import QueueUnavailable, get_job_queue
from app.main import app
from app.models import Tenant
from app.repositories import list_batches

TenantMaker = Callable[[str], tuple[Tenant, dict[str, str]]]


class DownQueue:
    """A queue whose Redis is not reachable."""

    def enqueue_batch_analysis(self, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> None:
        raise QueueUnavailable("Redis is down")


def test_upload_puts_one_job_in_the_queue(
    client: TestClient,
    make_tenant: TenantMaker,
    enqueued_jobs: list[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    tenant, headers = make_tenant("Tenant A")
    response = client.post("/batches", json={"reviews": ["bagus"]}, headers=headers)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert enqueued_jobs == [(tenant.id, uuid.UUID(response.json()["id"]))]


def test_the_job_uses_the_tenant_of_the_credentials(
    client: TestClient,
    make_tenant: TenantMaker,
    enqueued_jobs: list[tuple[uuid.UUID, uuid.UUID]],
) -> None:
    tenant_a, headers_a = make_tenant("Tenant A")
    tenant_b, _ = make_tenant("Tenant B")
    client.post(
        "/batches",
        json={"reviews": ["x"], "tenant_id": str(tenant_b.id)},
        headers=headers_a,
    )
    assert [tenant_id for tenant_id, _ in enqueued_jobs] == [tenant_a.id]


def test_a_batch_is_marked_failed_when_redis_is_down(
    client: TestClient, session: Session, make_tenant: TenantMaker
) -> None:
    tenant, headers = make_tenant("Tenant A")
    app.dependency_overrides[get_job_queue] = DownQueue
    response = client.post("/batches", json={"reviews": ["bagus"]}, headers=headers)
    assert response.status_code == 503
    batches = list_batches(session, tenant.id)
    assert len(batches) == 1
    assert batches[0].status == "failed"
    assert str(batches[0].id) in response.json()["detail"]


def test_upload_is_refused_before_saving_when_redis_is_not_configured(
    client: TestClient,
    session: Session,
    make_tenant: TenantMaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant, headers = make_tenant("Tenant A")
    monkeypatch.delenv("REDIS_URL", raising=False)
    app.dependency_overrides.pop(get_job_queue)
    response = client.post("/batches", json={"reviews": ["bagus"]}, headers=headers)
    assert response.status_code == 503
    assert len(list_batches(session, tenant.id)) == 0
