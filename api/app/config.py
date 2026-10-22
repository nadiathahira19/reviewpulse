"""Settings that are read from environment variables."""

import os


def get_signing_key() -> str:
    """Return the key that signs access tokens. It is never stored in the repository."""
    value = os.environ.get("JWT_SECRET")
    if not value:
        raise RuntimeError("JWT_SECRET is not set")
    return value


def get_database_url() -> str:
    """Return the address of the database."""
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not set")
    return value
