"""Background jobs. The worker (a later pull request) runs these functions."""

import uuid

import structlog
from sqlalchemy.orm import Session

from app.analyzer import SentimentAnalyzer, get_analyzer
from app.db import get_engine
from app.repositories import (
    get_batch,
    list_reviews,
    replace_predictions,
    set_batch_status,
)

logger = structlog.get_logger()


def analyze_batch(
    session: Session,
    analyzer: SentimentAnalyzer,
    tenant_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> int:
    """Analyze all reviews of a batch and save one prediction per review.

    The status goes pending -> processing -> done, or failed if anything goes wrong.
    Returns the number of analyzed reviews. Review texts are never logged.
    """
    if get_batch(session, tenant_id, batch_id) is None:
        raise LookupError("Batch not found for this tenant")
    log = logger.bind(tenant_id=str(tenant_id), batch_id=str(batch_id))
    set_batch_status(session, tenant_id, batch_id, "processing")
    log.info("batch_analysis_started")
    try:
        reviews = list_reviews(session, tenant_id, batch_id)
        results = analyzer.analyze([review.text for review in reviews])
        if len(results) != len(reviews):
            raise ValueError("The analyzer returned a different number of results")
        replace_predictions(
            session,
            tenant_id,
            [
                (review.id, result.label, result.score)
                for review, result in zip(reviews, results, strict=True)
            ],
            analyzer.model_version,
        )
    except Exception:
        session.rollback()
        set_batch_status(session, tenant_id, batch_id, "failed")
        log.exception("batch_analysis_failed")
        raise
    set_batch_status(session, tenant_id, batch_id, "done")
    log.info("batch_analysis_finished", review_count=len(reviews))
    return len(reviews)


def run_analyze_batch(tenant_id: str, batch_id: str) -> int:
    """Entry point for the worker. The arguments are strings, because a queue
    stores them as text."""
    with Session(get_engine()) as session:
        return analyze_batch(session, get_analyzer(), uuid.UUID(tenant_id), uuid.UUID(batch_id))
