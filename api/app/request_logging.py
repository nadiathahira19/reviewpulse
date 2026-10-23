"""Give every request an id and log how it ended."""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"

logger = structlog.get_logger()


async def request_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # The id is always generated here. An id sent by the client is not trusted.
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed", method=request.method, path=request.url.path)
        raise
    logger.info(
        "request_finished",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
