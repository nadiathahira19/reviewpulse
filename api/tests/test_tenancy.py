import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_signing_key
from app.db import get_session
from app.main import app
from app.models import ApiKey, Base, Tenant
from app.security import create_access_token, generate_api_key, hash_api_key

KEY = "unit-test-signing-key-0123456789abcdef"  # pragma: allowlist secret
OTHER_KEY = "another-test-signing-key-0123456789abc"  # pragma: allowlist secret


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


def make_tenant(session: Session) -> Tenant:
    tenant = Tenant(name="Test Tenant")
    session.add(tenant)
    session.commit()
    return tenant


def make_api_key(session: Session, tenant: Tenant, revoked: bool = False) -> str:
    plain_key = generate_api_key()
    row = ApiKey(tenant_id=tenant.id, name="test", key_hash=hash_api_key(plain_key))
    if revoked:
        from datetime import UTC, datetime

        row.revoked_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    return plain_key


def test_request_without_credentials_is_rejected(client: TestClient) -> None:
    assert client.get("/me").status_code == 401


def test_valid_token_identifies_the_tenant(client: TestClient) -> None:
    tenant_id = uuid.uuid4()
    token = create_access_token(uuid.uuid4(), tenant_id, KEY)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"tenant_id": str(tenant_id), "method": "token"}


def test_expired_token_is_rejected(client: TestClient) -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4(), KEY, expires_in=timedelta(seconds=-1))
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_token_signed_with_another_key_is_rejected(client: TestClient) -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4(), OTHER_KEY)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_valid_api_key_identifies_the_tenant(client: TestClient, session: Session) -> None:
    tenant = make_tenant(session)
    plain_key = make_api_key(session, tenant)
    response = client.get("/me", headers={"X-API-Key": plain_key})
    assert response.status_code == 200
    assert response.json() == {"tenant_id": str(tenant.id), "method": "api_key"}


def test_unknown_api_key_is_rejected(client: TestClient) -> None:
    response = client.get("/me", headers={"X-API-Key": generate_api_key()})
    assert response.status_code == 401


def test_revoked_api_key_is_rejected(client: TestClient, session: Session) -> None:
    tenant = make_tenant(session)
    plain_key = make_api_key(session, tenant, revoked=True)
    response = client.get("/me", headers={"X-API-Key": plain_key})
    assert response.status_code == 401


def test_tenant_cannot_be_chosen_by_the_client(client: TestClient) -> None:
    own_tenant = uuid.uuid4()
    other_tenant = uuid.uuid4()
    token = create_access_token(uuid.uuid4(), own_tenant, KEY)
    response = client.get(
        f"/me?tenant_id={other_tenant}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": str(other_tenant)},
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(own_tenant)


def test_bad_token_is_not_rescued_by_a_valid_api_key(client: TestClient, session: Session) -> None:
    tenant = make_tenant(session)
    plain_key = make_api_key(session, tenant)
    response = client.get(
        "/me", headers={"Authorization": "Bearer not.a.token", "X-API-Key": plain_key}
    )
    assert response.status_code == 401
