"""Database access. Every function needs a tenant_id, so data of one tenant cannot leak."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Prediction, Review, ReviewBatch


def create_batch(session: Session, tenant_id: uuid.UUID) -> ReviewBatch:
    """Create an empty batch for the tenant."""
    batch = ReviewBatch(tenant_id=tenant_id)
    session.add(batch)
    session.commit()
    session.refresh(batch)
    return batch


def create_batch_with_reviews(
    session: Session, tenant_id: uuid.UUID, texts: Sequence[str]
) -> ReviewBatch:
    """Create a batch and all its reviews in one transaction."""
    batch = ReviewBatch(tenant_id=tenant_id)
    session.add(batch)
    session.flush()  # gives the batch its id, nothing is saved for good yet
    session.add_all(Review(tenant_id=tenant_id, batch_id=batch.id, text=text) for text in texts)
    session.commit()
    session.refresh(batch)
    return batch


def list_batches(session: Session, tenant_id: uuid.UUID) -> Sequence[ReviewBatch]:
    """Return only the batches of this tenant."""
    statement = (
        select(ReviewBatch)
        .where(ReviewBatch.tenant_id == tenant_id)
        .order_by(ReviewBatch.created_at)
    )
    return session.scalars(statement).all()


def get_batch(session: Session, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> ReviewBatch | None:
    """Return the batch only if it belongs to this tenant."""
    statement = select(ReviewBatch).where(
        ReviewBatch.tenant_id == tenant_id,
        ReviewBatch.id == batch_id,
    )
    return session.scalars(statement).first()


def set_batch_status(
    session: Session, tenant_id: uuid.UUID, batch_id: uuid.UUID, status: str
) -> None:
    """Change the status of a batch of this tenant."""
    batch = get_batch(session, tenant_id, batch_id)
    if batch is None:
        raise LookupError("Batch not found for this tenant")
    batch.status = status
    session.commit()


def count_reviews(session: Session, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> int:
    """Count the reviews of a batch, only if the batch belongs to this tenant."""
    statement = (
        select(func.count())
        .select_from(Review)
        .where(Review.tenant_id == tenant_id, Review.batch_id == batch_id)
    )
    return session.scalar(statement) or 0


def list_reviews(session: Session, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> Sequence[Review]:
    """Return the reviews of a batch, only if the batch belongs to this tenant."""
    statement = (
        select(Review)
        .where(Review.tenant_id == tenant_id, Review.batch_id == batch_id)
        .order_by(Review.created_at, Review.id)
    )
    return session.scalars(statement).all()


def replace_predictions(
    session: Session,
    tenant_id: uuid.UUID,
    predictions: Sequence[tuple[uuid.UUID, str, float]],
    model_version: str,
) -> None:
    """Save (review_id, label, score) results. Old results of the same reviews are
    removed first, so running the same job twice does not create duplicates."""
    review_ids = [review_id for review_id, _, _ in predictions]
    session.execute(
        delete(Prediction).where(
            Prediction.tenant_id == tenant_id, Prediction.review_id.in_(review_ids)
        )
    )
    session.add_all(
        Prediction(
            tenant_id=tenant_id,
            review_id=review_id,
            label=label,
            score=score,
            model_version=model_version,
        )
        for review_id, label, score in predictions
    )
    session.commit()


def count_predictions(session: Session, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> int:
    """Count the saved results of a batch, only if the batch belongs to this tenant."""
    statement = (
        select(func.count())
        .select_from(Prediction)
        .join(Review, Review.id == Prediction.review_id)
        .where(
            Prediction.tenant_id == tenant_id,
            Review.tenant_id == tenant_id,
            Review.batch_id == batch_id,
        )
    )
    return session.scalar(statement) or 0
