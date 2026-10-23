import pytest

import app.analyzer as analyzer_module
from app.analyzer import FakeAnalyzer, get_analyzer


def test_fake_analyzer_is_used_when_model_name_is_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_NAME", raising=False)
    get_analyzer.cache_clear()
    try:
        assert isinstance(get_analyzer(), FakeAnalyzer)
    finally:
        get_analyzer.cache_clear()


def test_real_model_is_used_when_model_name_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyModel:
        def __init__(self, model_name: str) -> None:
            self.model_version = model_name

    monkeypatch.setenv("MODEL_NAME", "some/model")
    monkeypatch.setattr(analyzer_module, "TransformersAnalyzer", DummyModel)
    get_analyzer.cache_clear()
    try:
        assert get_analyzer().model_version == "some/model"
    finally:
        get_analyzer.cache_clear()
