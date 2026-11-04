"""Shared fixtures for the API controller tests.

The tests run against real PostgreSQL (the queries are Postgres-specific), but
never against the application's data: a throwaway schema is created for the
test session and dropped at the end, and every test runs inside a transaction
that is rolled back. The database comes from ``TEST_DATABASE_URL`` or, if that
is not set, ``DATABASE_URL``; the user only needs to own the database, not to
be able to create new ones. Without a reachable database, DB tests are skipped.
"""

import os
from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import app.main
from app.database import get_db
from app.main import app as fastapi_app
from app.models import Base, Country, Indicator, Observation, Sex, Source


def _no_db() -> Iterator[Session]:
    raise AssertionError("this test used the database without the db_session fixture")
    yield  # pragma: no cover - makes this a generator dependency like get_db


@pytest.fixture(autouse=True)
def _no_real_etl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if a test would download data or write the real database."""

    def forbidden() -> list[dict]:
        raise AssertionError("a test called the real ETL; monkeypatch it instead")

    monkeypatch.setattr(app.main, "extract_all", forbidden)
    monkeypatch.setattr(app.main, "load_all", forbidden)


@pytest.fixture
def client() -> Iterator[TestClient]:
    fastapi_app.dependency_overrides[get_db] = _no_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    load_dotenv()
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("set TEST_DATABASE_URL or DATABASE_URL to run database tests")

    schema = f"test_{uuid4().hex[:12]}"
    admin = create_engine(url)
    try:
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    except OperationalError as exc:
        admin.dispose()
        pytest.skip(f"PostgreSQL is not reachable: {exc.orig}")

    test_engine = create_engine(
        url, connect_args={"options": f"-csearch_path={schema}"}
    )
    try:
        Base.metadata.create_all(test_engine)
        yield test_engine
    finally:
        test_engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def db_session(engine: Engine, client: TestClient) -> Iterator[Session]:
    """A session whose work is rolled back after the test; used by the app too."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override() -> Iterator[Session]:
        yield session

    fastapi_app.dependency_overrides[get_db] = override
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# (iso3, indicator code, year, sex, value) for the seeded observations.
SEED_OBSERVATIONS = [
    ("ROU", "WHOSIS_000001", 2020, Sex.BOTH, Decimal("74.2")),
    ("ROU", "WHOSIS_000001", 2020, Sex.MALE, Decimal("70.9")),
    ("ROU", "WHOSIS_000001", 2020, Sex.FEMALE, Decimal("78.0")),
    ("ROU", "WHOSIS_000001", 2010, Sex.BOTH, Decimal("73.5")),
    ("ROU", "NY.GDP.PCAP.CD", 2020, Sex.BOTH, Decimal("13000")),
    ("FRA", "WHOSIS_000001", 2020, Sex.BOTH, Decimal("82.2")),
    ("FRA", "NY.GDP.PCAP.CD", 2015, Sex.BOTH, Decimal("36000")),
    ("KEN", "WHOSIS_000001", 2020, Sex.BOTH, Decimal("61.4")),
    ("KEN", "NY.GDP.PCAP.CD", 2000, Sex.BOTH, None),
]


@pytest.fixture
def seeded(db_session: Session) -> Session:
    """Three countries in two regions, two indicators, nine observations."""
    source = Source(name="Test source", url="https://example.org")
    db_session.add(source)
    db_session.add_all(
        [
            Country(iso3="ROU", iso2="RO", name="Romania",
                    region="Europe & Central Asia", income_group="High income"),
            Country(iso3="FRA", iso2="FR", name="France",
                    region="Europe & Central Asia", income_group="High income"),
            Country(iso3="KEN", iso2="KE", name="Kenya",
                    region="Sub-Saharan Africa", income_group="Lower middle income"),
        ]
    )
    db_session.flush()
    indicators = {
        "WHOSIS_000001": Indicator(code="WHOSIS_000001", name="Life expectancy at birth",
                                   unit="years", source_id=source.source_id),
        "NY.GDP.PCAP.CD": Indicator(code="NY.GDP.PCAP.CD", name="GDP per capita",
                                    unit="current US$", source_id=source.source_id),
    }
    db_session.add_all(indicators.values())
    db_session.flush()
    db_session.add_all(
        Observation(
            country_iso3=iso3,
            indicator_id=indicators[code].indicator_id,
            year=year,
            sex=sex,
            value=value,
        )
        for iso3, code, year, sex, value in SEED_OBSERVATIONS
    )
    db_session.flush()

    return db_session
