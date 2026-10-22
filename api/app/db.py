"""Database connection."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import get_database_url


@lru_cache
def get_engine() -> Engine:
    """Create the engine once and reuse it."""
    return create_engine(get_database_url())


def get_session() -> Iterator[Session]:
    """Give each request its own session and close it afterwards."""
    with Session(get_engine()) as session:
        yield session
