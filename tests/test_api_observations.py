"""GET /api/observations: JSON list with filters, ordering and paging."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("seeded")

URL = "/api/observations"


def _keys(rows: list[dict]) -> list[tuple]:
    return [(r["iso3"], r["indicator_code"], r["year"], r["sex"]) for r in rows]


def test_returns_all_rows_in_stable_order(client: TestClient) -> None:
    response = client.get(URL)

    assert response.status_code == 200
    # country name, year desc, indicator code, sex
    assert _keys(response.json()) == [
        ("FRA", "WHOSIS_000001", 2020, "BTSX"),
        ("FRA", "NY.GDP.PCAP.CD", 2015, "BTSX"),
        ("KEN", "WHOSIS_000001", 2020, "BTSX"),
        ("KEN", "NY.GDP.PCAP.CD", 2000, "BTSX"),
        ("ROU", "NY.GDP.PCAP.CD", 2020, "BTSX"),
        ("ROU", "WHOSIS_000001", 2020, "BTSX"),
        ("ROU", "WHOSIS_000001", 2020, "FMLE"),
        ("ROU", "WHOSIS_000001", 2020, "MLE"),
        ("ROU", "WHOSIS_000001", 2010, "BTSX"),
    ]


def test_row_contains_joined_country_and_indicator_fields(client: TestClient) -> None:
    rows = client.get(URL, params={"country": "FRA", "year_from": 2020}).json()

    assert rows == [
        {
            "country": "France",
            "iso3": "FRA",
            "region": "Europe & Central Asia",
            "indicator_code": "WHOSIS_000001",
            "indicator": "Life expectancy at birth",
            "unit": "years",
            "year": 2020,
            "sex": "BTSX",
            "value": 82.2,
        }
    ]


def test_missing_value_is_null(client: TestClient) -> None:
    rows = client.get(URL, params={"country": "KEN", "indicator": "NY.GDP.PCAP.CD"}).json()

    assert [r["value"] for r in rows] == [None]


@pytest.mark.parametrize(
    ("params", "expected_count"),
    [
        ({"country": "ROU"}, 5),
        ({"indicator": "NY.GDP.PCAP.CD"}, 3),
        ({"region": "Sub-Saharan Africa"}, 2),
        ({"year_from": 2015}, 7),
        ({"year_to": 2010}, 2),
        ({"country": "ROU", "year_from": 2011, "year_to": 2020}, 4),
        ({"country": "ROU", "indicator": "WHOSIS_000001", "year_to": 2010}, 1),
        ({"country": "XXX"}, 0),
    ],
)
def test_filters(client: TestClient, params: dict, expected_count: int) -> None:
    rows = client.get(URL, params=params).json()

    assert len(rows) == expected_count
    for row in rows:
        if "country" in params:
            assert row["iso3"] == params["country"]
        if "indicator" in params:
            assert row["indicator_code"] == params["indicator"]
        if "region" in params:
            assert row["region"] == params["region"]
        assert row["year"] >= params.get("year_from", row["year"])
        assert row["year"] <= params.get("year_to", row["year"])


def test_limit_and_offset_page_through_without_gaps_or_repeats(
    client: TestClient,
) -> None:
    everything = _keys(client.get(URL).json())

    pages = [
        _keys(client.get(URL, params={"limit": 4, "offset": offset}).json())
        for offset in (0, 4, 8)
    ]

    assert [len(page) for page in pages] == [4, 4, 1]
    assert [key for page in pages for key in page] == everything


def test_offset_past_the_end_returns_empty_list(client: TestClient) -> None:
    assert client.get(URL, params={"offset": 100}).json() == []


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 1001},
        {"offset": -1},
        {"year_from": "abc"},
        {"year_to": "2020.5"},
    ],
)
def test_invalid_query_parameters_are_rejected(client: TestClient, params: dict) -> None:
    assert client.get(URL, params=params).status_code == 422
