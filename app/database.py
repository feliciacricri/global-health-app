"""Database settings, engine and session factory.

Nothing connects or reads the environment at import time; everything is built
lazily on first use and cached, so tests can override ``get_db`` (FastAPI
``dependency_overrides``) or clear the caches before pointing at another DB.
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class Settings:
    database_url: str


@lru_cache
def get_settings() -> Settings:
    """Read settings from the environment (and ``.env``); fail if any are missing."""
    load_dotenv()
    try:
        database_url = os.environ["DATABASE_URL"]
    except KeyError:
        raise RuntimeError(
            "DATABASE_URL is not set; copy .env.example to .env and fill it in"
        ) from None
    return Settings(database_url=database_url)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False)


def get_db() -> Iterator[Session]:
    """One database session per request (used as a FastAPI dependency in later labs)."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
