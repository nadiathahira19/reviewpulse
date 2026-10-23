"""Database access. Every function needs a tenant_id, so data of one tenant cannot leak."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReviewBatch


def create_batch(session: Session, tenant_id: uuid.UUID) -> ReviewBatch:
    """Create an empty batch for the tenant."""
    batch = ReviewBatch(tenant_id=tenant_id)
    session.add(batch)
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
