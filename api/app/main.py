"""ReviewPulse API entrypoint."""

import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.repositories import get_batch, list_batches
from app.tenancy import CurrentTenant, get_current_tenant

app = FastAPI(title="ReviewPulse", version="0.1.0")

TenantDep = Annotated[CurrentTenant, Depends(get_current_tenant)]
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by Docker Compose and CI."""
    return {"status": "ok"}


@app.get("/me")
def me(current: TenantDep) -> dict[str, str]:
    """Show which tenant the request belongs to. Used to test authentication."""
    return {"tenant_id": str(current.tenant_id), "method": current.method}


@app.get("/batches")
def list_review_batches(current: TenantDep, session: SessionDep) -> list[dict[str, str]]:
    """List the batches of the current tenant."""
    batches = list_batches(session, current.tenant_id)
    return [{"id": str(batch.id), "status": batch.status} for batch in batches]


@app.get("/batches/{batch_id}")
def get_review_batch(
    batch_id: uuid.UUID, current: TenantDep, session: SessionDep
) -> dict[str, str]:
    """Return one batch. A batch of another tenant looks the same as a missing one."""
    batch = get_batch(session, current.tenant_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"id": str(batch.id), "status": batch.status}
