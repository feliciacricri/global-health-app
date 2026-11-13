"""Presentation layer (REST): the lookup lists under /api (full stack + DB)."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("seeded")


@pytest.fixture
def client(client_with_db: TestClient) -> TestClient:
    return client_with_db


def test_regions(client: TestClient) -> None:
    response = client.get("/api/regions")

    assert response.status_code == 200
    assert response.json() == ["Europe & Central Asia", "Sub-Saharan Africa"]


def test_countries_sorted_by_name(client: TestClient) -> None:
    assert client.get("/api/countries").json() == [
        {"iso3": "FRA", "name": "France"},
        {"iso3": "KEN", "name": "Kenya"},
        {"iso3": "XKX", "name": "Kosovo"},
        {"iso3": "ROU", "name": "Romania"},
    ]


def test_countries_of_one_region(client: TestClient) -> None:
    response = client.get("/api/countries", params={"region": "Europe & Central Asia"})

    assert response.json() == [
        {"iso3": "FRA", "name": "France"},
        {"iso3": "ROU", "name": "Romania"},
    ]


def test_indicators(client: TestClient) -> None:
    assert client.get("/api/indicators").json() == [
        {"code": "NY.GDP.PCAP.CD", "name": "GDP per capita"},
        {"code": "WHOSIS_000001", "name": "Life expectancy at birth"},
    ]


def test_openapi_describes_only_the_json_api(client: TestClient) -> None:
    paths = client.get("/api/openapi.json").json()["paths"]

    assert sorted(paths) == [
        "/api/countries",
        "/api/indicators",
        "/api/regions",
    ]
