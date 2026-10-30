"""Shared test fixtures."""

import os
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analyzer import get_analyzer
from app.config import get_signing_key
from app.db import get_session
from app.main import app
from app.models import Base, Tenant
from app.security import create_access_token

SIGNING_KEY = "unit-test-signing-key-0123456789abcdef"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def use_fake_analyzer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never load the real model, even if MODEL_NAME is set in the terminal."""
    monkeypatch.delenv("MODEL_NAME", raising=False)
    get_analyzer.cache_clear()


@pytest.fixture
def session() -> Iterator[Session]:
    """Postgres when DATABASE_URL is set (CI), in-memory SQLite otherwise."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url)
    else:
        engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_signing_key] = lambda: SIGNING_KEY
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_tenant(session: Session) -> Callable[[str], tuple[Tenant, dict[str, str]]]:
    """Create a tenant and return it together with valid login headers."""

    def _make(name: str) -> tuple[Tenant, dict[str, str]]:
        tenant = Tenant(name=name)
        session.add(tenant)
        session.commit()
        token = create_access_token(uuid.uuid4(), tenant.id, SIGNING_KEY)
        return tenant, {"Authorization": f"Bearer {token}"}

    return _make
