import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analyzer import FakeAnalyzer, SentimentResult, get_analyzer
from app.config import get_signing_key
from app.db import get_session
from app.main import app
from app.models import Base, Tenant
from app.security import create_access_token

KEY = "unit-test-signing-key-0123456789abcdef"  # pragma: allowlist secret


class StubAnalyzer:
    model_version: str = "stub-v1"

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        return [SentimentResult(label="positive", score=1.0) for _ in texts]


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


@pytest.fixture
def auth_headers(session: Session) -> dict[str, str]:
    tenant = Tenant(name="Tenant A")
    session.add(tenant)
    session.commit()
    token = create_access_token(uuid.uuid4(), tenant.id, KEY)
    return {"Authorization": f"Bearer {token}"}


def test_fake_analyzer_labels_positive_negative_and_neutral() -> None:
    results = FakeAnalyzer().analyze(
        ["Produknya bagus, aku suka", "Kulitku iritasi, kecewa", "Dikirim hari Selasa"]
    )
    assert [result.label for result in results] == ["positive", "negative", "neutral"]


def test_fake_analyzer_treats_mixed_feelings_as_neutral() -> None:
    result = FakeAnalyzer().analyze(["Bagus tapi jelek"])[0]
    assert result.label == "neutral"


def test_analyze_returns_one_result_per_review(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/reviews/analyze",
        json={"reviews": ["Mantap, cocok di kulitku", "Buruk sekali"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "fake-keyword-v0"
    assert [item["index"] for item in body["results"]] == [0, 1]
    assert [item["label"] for item in body["results"]] == ["positive", "negative"]


def test_analyze_uses_the_analyzer_dependency(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    app.dependency_overrides[get_analyzer] = StubAnalyzer
    response = client.post("/reviews/analyze", json={"reviews": ["apa saja"]}, headers=auth_headers)
    assert response.json()["model_version"] == "stub-v1"


def test_analyze_requires_credentials(client: TestClient) -> None:
    response = client.post("/reviews/analyze", json={"reviews": ["bagus"]})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"reviews": []},
        {"reviews": [""]},
        {"reviews": ["bagus"] * 101},
        {"reviews": ["a" * 2001]},
        {},
    ],
)
def test_analyze_rejects_invalid_input(
    client: TestClient, auth_headers: dict[str, str], payload: dict[str, list[str]]
) -> None:
    response = client.post("/reviews/analyze", json=payload, headers=auth_headers)
    assert response.status_code == 422
