"""Service layer: periods, validation and the per-country series, with an
in-memory repository (no database)."""

from decimal import Decimal

import pytest

from app.domain import IndicatorInfo, PeriodAverage, PeriodAverageQuery
from app.models import Sex
from app.services.period_average_service import (
    MAX_COUNTRIES,
    CountrySeries,
    InvalidQueryError,
    Period,
    PeriodAverageService,
    UnknownIndicatorError,
)

LIFE_EXPECTANCY = IndicatorInfo("OWID_LIFE_EXPECTANCY", "Life expectancy", "years")


class FakeRepository:
    def __init__(self, averages: list[PeriodAverage]) -> None:
        self._averages = averages
        self.calls: list[tuple[PeriodAverageQuery, Sex]] = []

    def find_indicator(self, code: str) -> IndicatorInfo | None:
        return LIFE_EXPECTANCY if code == LIFE_EXPECTANCY.code else None

    def average_by_period(
        self, query: PeriodAverageQuery, *, sex: Sex
    ) -> list[PeriodAverage]:
        self.calls.append((query, sex))
        return self._averages


def _query(**overrides) -> PeriodAverageQuery:
    values = {
        "indicator_code": LIFE_EXPECTANCY.code,
        "country_iso3s": ("FRA", "ROU"),
        "first_year": 2000,
        "last_year": 2023,
        "period_years": 5,
    } | overrides
    return PeriodAverageQuery(**values)


def test_report_has_one_series_per_country_aligned_with_the_periods() -> None:
    repository = FakeRepository(
        [
            PeriodAverage("FRA", "France", 2000, Decimal("79.4875"), 5),
            PeriodAverage("ROU", "Romania", 2005, Decimal("72.6"), 5),
            PeriodAverage("ROU", "Romania", 2020, Decimal("74.505"), 4),
        ]
    )
    query = _query()

    report = PeriodAverageService(repository).get_report(query)

    assert repository.calls == [(query, Sex.BOTH)]
    assert report.indicator == LIFE_EXPECTANCY
    assert report.periods == (
        Period(2000, 2004),
        Period(2005, 2009),
        Period(2010, 2014),
        Period(2015, 2019),
        Period(2020, 2023),
    )
    # Rounded to 2 decimals; None where a country has no data.
    assert report.series == (
        CountrySeries("FRA", "France", (Decimal("79.49"), None, None, None, None)),
        CountrySeries(
            "ROU", "Romania", (None, Decimal("72.60"), None, None, Decimal("74.51"))
        ),
    )


@pytest.mark.parametrize(
    ("first_year", "last_year", "period_years", "expected"),
    [
        (2000, 2009, 5, [(2000, 2004), (2005, 2009)]),
        (2000, 2001, 5, [(2000, 2001)]),
        (2020, 2020, 1, [(2020, 2020)]),
        (2000, 2006, 3, [(2000, 2002), (2003, 2005), (2006, 2006)]),
    ],
)
def test_periods_cover_the_years_and_the_last_one_may_be_shorter(
    first_year: int, last_year: int, period_years: int, expected: list[tuple[int, int]]
) -> None:
    query = _query(
        first_year=first_year, last_year=last_year, period_years=period_years
    )

    report = PeriodAverageService(FakeRepository([])).get_report(query)

    assert [(p.start, p.end) for p in report.periods] == expected
    assert report.series == ()


@pytest.mark.parametrize(
    ("period", "label"),
    [(Period(2000, 2004), "2000–2004"), (Period(2020, 2020), "2020")],
)
def test_period_label(period: Period, label: str) -> None:
    assert period.label == label


def test_unknown_indicator() -> None:
    service = PeriodAverageService(FakeRepository([]))

    with pytest.raises(UnknownIndicatorError, match="'NOPE'"):
        service.get_report(_query(indicator_code="NOPE"))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"period_years": 0}, "period_years must be at least 1"),
        (
            {"first_year": 2010, "last_year": 2009},
            "first_year 2010 is after last_year 2009",
        ),
        (
            {"country_iso3s": tuple(f"C{n:02}" for n in range(MAX_COUNTRIES + 1))},
            f"at most {MAX_COUNTRIES} countries",
        ),
    ],
)
def test_invalid_queries_never_reach_the_repository(
    overrides: dict, message: str
) -> None:
    repository = FakeRepository([])

    with pytest.raises(InvalidQueryError, match=message):
        PeriodAverageService(repository).get_report(_query(**overrides))
    assert repository.calls == []
