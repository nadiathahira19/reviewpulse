import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logging_config import configure_logging
from app.main import app as real_app
from app.request_logging import REQUEST_ID_HEADER, request_logging_middleware


def make_app() -> FastAPI:
    test_app = FastAPI()
    test_app.middleware("http")(request_logging_middleware)

    @test_app.get("/ok")
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("boom")

    return test_app


def read_logs(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    lines = capsys.readouterr().out.strip().splitlines()
    return [json.loads(line) for line in lines]


def test_request_is_logged_as_json_with_the_request_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging()
    response = TestClient(make_app()).get("/ok")
    entry = read_logs(capsys)[-1]
    assert entry["event"] == "request_finished"
    assert entry["level"] == "info"
    assert entry["method"] == "GET"
    assert entry["path"] == "/ok"
    assert entry["status_code"] == 200
    assert "timestamp" in entry
    assert "duration_ms" in entry
    assert entry["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_every_request_gets_its_own_id() -> None:
    client = TestClient(make_app())
    first = client.get("/ok").headers[REQUEST_ID_HEADER]
    second = client.get("/ok").headers[REQUEST_ID_HEADER]
    assert first != second


def test_a_failing_request_is_logged_with_the_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging()
    with pytest.raises(RuntimeError):
        TestClient(make_app()).get("/boom")
    entry = read_logs(capsys)[-1]
    assert entry["event"] == "request_failed"
    assert entry["level"] == "error"
    assert "RuntimeError" in str(entry["exception"])
    assert "request_id" in entry


def test_the_real_app_returns_a_request_id() -> None:
    response = TestClient(real_app).get("/healthz")
    assert REQUEST_ID_HEADER in response.headers
