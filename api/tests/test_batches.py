import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Tenant
from app.repositories import count_reviews, create_batch_with_reviews, list_batches

TenantMaker = Callable[[str], tuple[Tenant, dict[str, str]]]


def test_upload_stores_the_batch_and_all_reviews(
    client: TestClient, session: Session, make_tenant: TenantMaker
) -> None:
    tenant, headers = make_tenant("Tenant A")
    response = client.post(
        "/batches", json={"reviews": ["bagus", "jelek", "biasa"]}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["review_count"] == 3
    assert count_reviews(session, tenant.id, uuid.UUID(body["id"])) == 3


def test_uploaded_batch_can_be_read_with_its_review_count(
    client: TestClient, make_tenant: TenantMaker
) -> None:
    _, headers = make_tenant("Tenant A")
    created = client.post("/batches", json={"reviews": ["a", "b"]}, headers=headers)
    response = client.get(f"/batches/{created.json()['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["review_count"] == 2


def test_another_tenant_cannot_see_the_uploaded_batch(
    client: TestClient, make_tenant: TenantMaker
) -> None:
    _, headers_a = make_tenant("Tenant A")
    _, headers_b = make_tenant("Tenant B")
    created = client.post("/batches", json={"reviews": ["a"]}, headers=headers_a)
    batch_id = created.json()["id"]
    assert client.get(f"/batches/{batch_id}", headers=headers_b).status_code == 404
    assert client.get("/batches", headers=headers_b).json() == []


def test_batch_belongs_to_the_tenant_of_the_credentials(
    client: TestClient, session: Session, make_tenant: TenantMaker
) -> None:
    tenant_a, headers_a = make_tenant("Tenant A")
    tenant_b, _ = make_tenant("Tenant B")
    client.post(
        "/batches",
        json={"reviews": ["x"], "tenant_id": str(tenant_b.id)},
        headers=headers_a,
    )
    assert len(list_batches(session, tenant_a.id)) == 1
    assert len(list_batches(session, tenant_b.id)) == 0


def test_upload_requires_credentials(client: TestClient) -> None:
    response = client.post("/batches", json={"reviews": ["a"]})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"reviews": []},
        {"reviews": [""]},
        {"reviews": ["a"] * 1001},
        {"reviews": ["a" * 2001]},
    ],
)
def test_upload_rejects_invalid_input(
    client: TestClient,
    make_tenant: TenantMaker,
    payload: dict[str, list[str]],
) -> None:
    _, headers = make_tenant("Tenant A")
    response = client.post("/batches", json=payload, headers=headers)
    assert response.status_code == 422


def test_count_reviews_is_scoped_to_the_tenant(session: Session, make_tenant: TenantMaker) -> None:
    tenant_a, _ = make_tenant("Tenant A")
    tenant_b, _ = make_tenant("Tenant B")
    batch = create_batch_with_reviews(session, tenant_a.id, ["x", "y"])
    assert count_reviews(session, tenant_a.id, batch.id) == 2
    assert count_reviews(session, tenant_b.id, batch.id) == 0
