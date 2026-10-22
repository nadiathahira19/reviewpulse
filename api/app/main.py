"""ReviewPulse API entrypoint."""

from typing import Annotated

from fastapi import Depends, FastAPI

from app.tenancy import CurrentTenant, get_current_tenant

app = FastAPI(title="ReviewPulse", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by Docker Compose and CI."""
    return {"status": "ok"}


@app.get("/me")
def me(current: Annotated[CurrentTenant, Depends(get_current_tenant)]) -> dict[str, str]:
    """Show which tenant the request belongs to. Used to test authentication."""
    return {"tenant_id": str(current.tenant_id), "method": current.method}
