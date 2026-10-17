"""ReviewPulse API entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="ReviewPulse", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe used by Docker Compose and CI."""
    return {"status": "ok"}
