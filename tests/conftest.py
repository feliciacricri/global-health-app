"""Shared fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_etl_service
from app.main import app


def _no_database() -> Iterator[Session]:
    raise AssertionError("this test used the database without the db_session fixture")
    yield  # pragma: no cover - makes this a generator dependency like get_db


def _no_real_etl() -> None:
    raise AssertionError("this test ran the real ETL; override get_etl_service")


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client that can reach neither the database nor the real ETL."""
    app.dependency_overrides[get_db] = _no_database
    app.dependency_overrides[get_etl_service] = _no_real_etl
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
