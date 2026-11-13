"""Presentation layer (REST): GET /api/indicators/{code}/period-averages."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_period_average_service
from app.domain import IndicatorInfo, PeriodAverageQuery
from app.main import app
from app.services.period_average_service import (
    CountrySeries,
    InvalidQueryError,
    Period,
    PeriodAverageReport,
    UnknownIndicatorError,
)

URL = "/api/indicators/WHOSIS_000001/period-averages"

REPORT = PeriodAverageReport(
    indicator=IndicatorInfo("WHOSIS_000001", "Life expectancy at birth", "years"),
    periods=(Period(2000, 2004), Period(2005, 2005)),
    series=(CountrySeries("ROU", "Romania", (Decimal("71.01"), None)),),
)


class FakeService:
    """Returns a fixed report, or raises ``error``; records the queries."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.queries: list[PeriodAverageQuery] = []

    def get_report(self, query: PeriodAverageQuery) -> PeriodAverageReport:
        self.queries.append(query)
        if self._error is not None:
            raise self._error
        return REPORT


def _use(service: FakeService) -> FakeService:
    app.dependency_overrides[get_period_average_service] = lambda: service
    return service


def test_report_as_json(client: TestClient) -> None:
    _use(FakeService())

    response = client.get(URL)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "indicator": {
            "code": "WHOSIS_000001",
            "name": "Life expectancy at birth",
            "unit": "years",
        },
        "periods": [
            {"start": 2000, "end": 2004, "label": "2000–2004"},
            {"start": 2005, "end": 2005, "label": "2005"},
        ],
        # Numbers, not strings, so a client can chart them as they are.
        "series": [
            {"country_iso3": "ROU", "country_name": "Romania", "averages": [71.01, None]}
        ],
    }


def test_query_string_becomes_the_service_query(client: TestClient) -> None:
    service = _use(FakeService())

    client.get(
        URL,
        params={
            "country": ["ROU", "FRA", "ROU"],
            "first_year": 2005,
            "last_year": 2019,
            "period_years": 3,
        },
    )

    assert service.queries == [
        PeriodAverageQuery("WHOSIS_000001", ("ROU", "FRA"), 2005, 2019, 3)
    ]


def test_defaults_cover_2000_to_2023_in_5_year_periods(client: TestClient) -> None:
    service = _use(FakeService())

    client.get(URL)

    assert service.queries == [PeriodAverageQuery("WHOSIS_000001", (), 2000, 2023, 5)]


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (UnknownIndicatorError("unknown indicator 'WHOSIS_000001'"), 404),
        (InvalidQueryError("first_year 2010 is after last_year 2009"), 422),
    ],
)
def test_service_errors_become_http_errors(
    client: TestClient, error: Exception, status_code: int
) -> None:
    _use(FakeService(error))

    response = client.get(URL)

    assert response.status_code == status_code
    assert response.json() == {"detail": str(error)}


@pytest.mark.parametrize(
    "params", [{"period_years": "0"}, {"first_year": "abc"}]
)
def test_malformed_parameters_are_rejected_before_the_service(
    client: TestClient, params: dict[str, str]
) -> None:
    service = _use(FakeService())

    response = client.get(URL, params=params)

    assert response.status_code == 422
    assert service.queries == []


@pytest.mark.usefixtures("seeded")
def test_full_stack_against_the_database(client_with_db: TestClient) -> None:
    response = client_with_db.get(
        URL, params={"country": ["ROU", "FRA", "KEN"], "first_year": 2010}
    )

    assert response.status_code == 200
    body = response.json()
    assert [p["label"] for p in body["periods"]] == [
        "2010–2014", "2015–2019", "2020–2023"
    ]
    assert [(s["country_iso3"], s["averages"]) for s in body["series"]] == [
        ("FRA", [None, None, 82.2]),
        ("KEN", [None, None, 61.4]),
        ("ROU", [73.5, None, 74.2]),
    ]
