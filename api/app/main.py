"""ReviewPulse API entrypoint."""

import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analyzer import SentimentAnalyzer, get_analyzer
from app.db import get_session
from app.logging_config import configure_logging
from app.repositories import (
    count_reviews,
    create_batch_with_reviews,
    get_batch,
    list_batches,
)
from app.request_logging import request_logging_middleware
from app.tenancy import CurrentTenant, get_current_tenant

app = FastAPI(title="ReviewPulse", version="0.1.0")
configure_logging()
app.middleware("http")(request_logging_middleware)

TenantDep = Annotated[CurrentTenant, Depends(get_current_tenant)]
SessionDep = Annotated[Session, Depends(get_session)]
AnalyzerDep = Annotated[SentimentAnalyzer, Depends(get_analyzer)]

ReviewText = Annotated[str, Field(min_length=1, max_length=2000)]


class AnalyzeRequest(BaseModel):
    reviews: list[ReviewText] = Field(min_length=1, max_length=100)


class ReviewResult(BaseModel):
    index: int
    label: str
    score: float


class AnalyzeResponse(BaseModel):
    model_version: str
    results: list[ReviewResult]


class BatchCreateRequest(BaseModel):
    reviews: list[ReviewText] = Field(min_length=1, max_length=1000)


class BatchCreated(BaseModel):
    id: str
    status: str
    review_count: int


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by Docker Compose and CI."""
    return {"status": "ok"}


@app.get("/me")
def me(current: TenantDep) -> dict[str, str]:
    """Show which tenant the request belongs to. Used to test authentication."""
    return {"tenant_id": str(current.tenant_id), "method": current.method}


@app.post("/batches", status_code=201)
def create_review_batch(
    body: BatchCreateRequest, current: TenantDep, session: SessionDep
) -> BatchCreated:
    """Upload up to 1000 reviews as one batch of the current tenant."""
    batch = create_batch_with_reviews(session, current.tenant_id, body.reviews)
    return BatchCreated(id=str(batch.id), status=batch.status, review_count=len(body.reviews))


@app.get("/batches")
def list_review_batches(current: TenantDep, session: SessionDep) -> list[dict[str, str]]:
    """List the batches of the current tenant."""
    batches = list_batches(session, current.tenant_id)
    return [{"id": str(batch.id), "status": batch.status} for batch in batches]


@app.get("/batches/{batch_id}")
def get_review_batch(
    batch_id: uuid.UUID, current: TenantDep, session: SessionDep
) -> dict[str, str | int]:
    """Return one batch. A batch of another tenant looks the same as a missing one."""
    batch = get_batch(session, current.tenant_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {
        "id": str(batch.id),
        "status": batch.status,
        "review_count": count_reviews(session, current.tenant_id, batch.id),
    }


@app.post("/reviews/analyze", dependencies=[Depends(get_current_tenant)])
def analyze_reviews(body: AnalyzeRequest, analyzer: AnalyzerDep) -> AnalyzeResponse:
    """Analyze the sentiment of up to 100 reviews. Needs credentials, nothing is stored yet."""
    results = analyzer.analyze(body.reviews)
    return AnalyzeResponse(
        model_version=analyzer.model_version,
        results=[
            ReviewResult(index=i, label=result.label, score=result.score)
            for i, result in enumerate(results)
        ],
    )
