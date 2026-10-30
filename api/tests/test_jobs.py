from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.jobs as jobs_module
from app.analyzer import FakeAnalyzer, SentimentResult
from app.jobs import analyze_batch, run_analyze_batch
from app.models import Tenant
from app.repositories import count_predictions, create_batch_with_reviews, get_batch

TenantMaker = Callable[[str], tuple[Tenant, dict[str, str]]]

TEXTS = ["Produknya bagus, aku suka", "Kecewa dan iritasi", "Dikirim hari Selasa"]


class BrokenAnalyzer:
    model_version: str = "broken-v0"

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        raise RuntimeError("model crashed")


class WrongCountAnalyzer:
    model_version: str = "wrong-count-v0"

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        return []


def test_analyze_batch_saves_one_prediction_per_review(
    session: Session, make_tenant: TenantMaker
) -> None:
    tenant, _ = make_tenant("Tenant A")
    batch = create_batch_with_reviews(session, tenant.id, TEXTS)
    assert analyze_batch(session, FakeAnalyzer(), tenant.id, batch.id) == 3
    assert count_predictions(session, tenant.id, batch.id) == 3
    saved = get_batch(session, tenant.id, batch.id)
    assert saved is not None
    assert saved.status == "done"


def test_running_the_job_twice_does_not_create_duplicates(
    session: Session, make_tenant: TenantMaker
) -> None:
    tenant, _ = make_tenant("Tenant A")
    batch = create_batch_with_reviews(session, tenant.id, TEXTS)
    analyze_batch(session, FakeAnalyzer(), tenant.id, batch.id)
    analyze_batch(session, FakeAnalyzer(), tenant.id, batch.id)
    assert count_predictions(session, tenant.id, batch.id) == 3


@pytest.mark.parametrize("analyzer", [BrokenAnalyzer(), WrongCountAnalyzer()])
def test_a_failing_analysis_marks_the_batch_as_failed(
    session: Session,
    make_tenant: TenantMaker,
    analyzer: BrokenAnalyzer | WrongCountAnalyzer,
) -> None:
    tenant, _ = make_tenant("Tenant A")
    batch = create_batch_with_reviews(session, tenant.id, TEXTS)
    with pytest.raises((RuntimeError, ValueError)):
        analyze_batch(session, analyzer, tenant.id, batch.id)
    assert count_predictions(session, tenant.id, batch.id) == 0
    saved = get_batch(session, tenant.id, batch.id)
    assert saved is not None
    assert saved.status == "failed"


def test_a_tenant_cannot_analyze_the_batch_of_another_tenant(
    session: Session, make_tenant: TenantMaker
) -> None:
    tenant_a, _ = make_tenant("Tenant A")
    tenant_b, _ = make_tenant("Tenant B")
    batch = create_batch_with_reviews(session, tenant_a.id, TEXTS)
    with pytest.raises(LookupError):
        analyze_batch(session, FakeAnalyzer(), tenant_b.id, batch.id)
    assert count_predictions(session, tenant_a.id, batch.id) == 0
    saved = get_batch(session, tenant_a.id, batch.id)
    assert saved is not None
    assert saved.status == "pending"


def test_count_predictions_is_scoped_to_the_tenant(
    session: Session, make_tenant: TenantMaker
) -> None:
    tenant_a, _ = make_tenant("Tenant A")
    tenant_b, _ = make_tenant("Tenant B")
    batch = create_batch_with_reviews(session, tenant_a.id, TEXTS)
    analyze_batch(session, FakeAnalyzer(), tenant_a.id, batch.id)
    assert count_predictions(session, tenant_a.id, batch.id) == 3
    assert count_predictions(session, tenant_b.id, batch.id) == 0


def test_worker_entry_point_opens_its_own_session(
    session: Session, make_tenant: TenantMaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant, _ = make_tenant("Tenant A")
    batch = create_batch_with_reviews(session, tenant.id, TEXTS[:2])
    monkeypatch.setattr(jobs_module, "get_engine", lambda: session.get_bind())
    assert run_analyze_batch(str(tenant.id), str(batch.id)) == 2
    session.expire_all()
    assert count_predictions(session, tenant.id, batch.id) == 2


def test_batch_detail_shows_how_many_reviews_are_analyzed(
    client: TestClient, session: Session, make_tenant: TenantMaker
) -> None:
    tenant, headers = make_tenant("Tenant A")
    batch = create_batch_with_reviews(session, tenant.id, TEXTS[:2])
    before = client.get(f"/batches/{batch.id}", headers=headers).json()
    analyze_batch(session, FakeAnalyzer(), tenant.id, batch.id)
    after = client.get(f"/batches/{batch.id}", headers=headers).json()
    assert before["analyzed_count"] == 0
    assert after["analyzed_count"] == 2
    assert after["status"] == "done"
