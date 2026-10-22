import pytest

from app.config import get_database_url, get_signing_key


def test_settings_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert get_signing_key() == "x" * 40
    assert get_database_url() == "sqlite://"


def test_missing_settings_raise_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        get_signing_key()
    with pytest.raises(RuntimeError):
        get_database_url()
