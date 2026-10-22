import re
import uuid
from collections.abc import Iterator

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_signing_key
from app.db import get_session
from app.main import app
from app.models import ApiKey, Base, Tenant
from app.repositories import create_batch, list_batches
from app.security import create_access_token, generate_api_key, hash_api_key

KEY = "unit-test-signing-key-0123456789abcdef"  # pragma: allowlist secret
PUBLIC_PATHS = {"/healthz"}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_signing_key] = lambda: KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


class World:
    """Two tenants, each with their own batches."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.tenant_a = self._tenant("Tenant A")
        self.tenant_b = self._tenant("Tenant B")
        self.batches_a = {create_batch(session, self.tenant_a.id).id for _ in range(2)}
        self.batches_b = {create_batch(session, self.tenant_b.id).id for _ in range(1)}

    def _tenant(self, name: str) -> Tenant:
        tenant = Tenant(name=name)
        self.session.add(tenant)
        self.session.commit()
        return tenant

    def token(self, tenant: Tenant) -> dict[str, str]:
        token = create_access_token(uuid.uuid4(), tenant.id, KEY)
        return {"Authorization": f"Bearer {token}"}

    def api_key_header(self, tenant: Tenant) -> dict[str, str]:
        plain_key = generate_api_key()
        row = ApiKey(tenant_id=tenant.id, name="test", key_hash=hash_api_key(plain_key))
        self.session.add(row)
        self.session.commit()
        return {"X-API-Key": plain_key}


@pytest.fixture
def world(session: Session) -> World:
    return World(session)


def ids(response_json: list[dict[str, str]]) -> set[uuid.UUID]:
    return {uuid.UUID(item["id"]) for item in response_json}


def test_repository_returns_only_the_tenants_own_batches(world: World) -> None:
    own = {batch.id for batch in list_batches(world.session, world.tenant_a.id)}
    assert own == world.batches_a
    assert own.isdisjoint(world.batches_b)


def test_listing_shows_only_own_batches(client: TestClient, world: World) -> None:
    response_a = client.get("/batches", headers=world.token(world.tenant_a))
    response_b = client.get("/batches", headers=world.token(world.tenant_b))
    assert ids(response_a.json()) == world.batches_a
    assert ids(response_b.json()) == world.batches_b


def test_own_batch_can_be_read(client: TestClient, world: World) -> None:
    batch_id = next(iter(world.batches_a))
    response = client.get(f"/batches/{batch_id}", headers=world.token(world.tenant_a))
    assert response.status_code == 200


def test_another_tenants_batch_looks_like_it_does_not_exist(
    client: TestClient, world: World
) -> None:
    other_batch = next(iter(world.batches_b))
    response = client.get(f"/batches/{other_batch}", headers=world.token(world.tenant_a))
    assert response.status_code == 404


def test_client_cannot_choose_the_tenant(client: TestClient, world: World) -> None:
    headers = {**world.token(world.tenant_a), "X-Tenant-Id": str(world.tenant_b.id)}
    response = client.get(f"/batches?tenant_id={world.tenant_b.id}", headers=headers)
    assert ids(response.json()) == world.batches_a


def test_api_key_sees_only_its_own_tenant(client: TestClient, world: World) -> None:
    response = client.get("/batches", headers=world.api_key_header(world.tenant_b))
    assert ids(response.json()) == world.batches_b


def test_every_route_except_public_ones_requires_credentials(client: TestClient) -> None:
    checked = 0
    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in PUBLIC_PATHS:
            continue
        path = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), route.path)
        for method in route.methods or []:
            response = client.request(method, path)
            assert response.status_code == 401, (method, route.path)
            checked += 1
    assert checked >= 3
