"""Data access layer: per-period averages computed by PostgreSQL."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import IndicatorInfo, PeriodAverage, PeriodAverageQuery
from app.models import Indicator, Observation, Sex
from app.repositories.period_average_repository import PeriodAverageRepository

LIFE_EXPECTANCY = "WHOSIS_000001"


@pytest.fixture
def repository(seeded: Session) -> PeriodAverageRepository:
    """The seeded data plus two more Romanian years: 2012 with a value and
    2013 without one (the seed already has 2010 and 2020)."""
    indicator_id = seeded.scalar(
        select(Indicator.indicator_id).where(Indicator.code == LIFE_EXPECTANCY)
    )
    seeded.add_all(
        [
            Observation(country_iso3="ROU", indicator_id=indicator_id, year=2012,
                        sex=Sex.BOTH, value=Decimal("74.5")),
            Observation(country_iso3="ROU", indicator_id=indicator_id, year=2013,
                        sex=Sex.BOTH, value=None),
        ]
    )
    seeded.flush()
    return PeriodAverageRepository(seeded)


def _query(countries: tuple[str, ...], **years: int) -> PeriodAverageQuery:
    years = {"first_year": 2000, "last_year": 2023, "period_years": 5} | years
    return PeriodAverageQuery(
        indicator_code=LIFE_EXPECTANCY, country_iso3s=countries, **years
    )


def test_find_indicator(repository: PeriodAverageRepository) -> None:
    assert repository.find_indicator(LIFE_EXPECTANCY) == IndicatorInfo(
        LIFE_EXPECTANCY, "Life expectancy at birth", "years"
    )
    assert repository.find_indicator("NOPE") is None


def test_averages_per_country_and_period_skip_missing_values_and_other_sexes(
    repository: PeriodAverageRepository,
) -> None:
    averages = repository.average_by_period(_query(("ROU", "FRA")), sex=Sex.BOTH)

    # Ordered by country name, then period. 2013 has no value, and the 2020
    # male and female rows are not part of the both-sexes average.
    assert [
        (a.country_iso3, a.country_name, a.period_start, a.observation_count)
        for a in averages
    ] == [
        ("FRA", "France", 2020, 1),
        ("ROU", "Romania", 2010, 2),
        ("ROU", "Romania", 2020, 1),
    ]
    assert [a.average for a in averages] == [
        Decimal("82.2"), Decimal("74.0"), Decimal("74.2")
    ]


def test_periods_start_at_first_year(repository: PeriodAverageRepository) -> None:
    averages = repository.average_by_period(
        _query(("ROU",), first_year=2008, period_years=4), sex=Sex.BOTH
    )

    # 2010 is in 2008-2011, 2012 in 2012-2015, 2020 in 2020-2023.
    assert [(a.period_start, a.average) for a in averages] == [
        (2008, Decimal("73.5")), (2012, Decimal("74.5")), (2020, Decimal("74.2"))
    ]


def test_years_outside_the_range_are_ignored(
    repository: PeriodAverageRepository,
) -> None:
    averages = repository.average_by_period(
        _query(("ROU",), first_year=2011, last_year=2019), sex=Sex.BOTH
    )

    assert averages == [PeriodAverage("ROU", "Romania", 2011, Decimal("74.5"), 1)]


def test_only_the_requested_countries_and_sex(
    repository: PeriodAverageRepository,
) -> None:
    assert repository.average_by_period(_query(()), sex=Sex.BOTH) == []

    female = repository.average_by_period(_query(("ROU", "KEN")), sex=Sex.FEMALE)

    assert [(a.country_iso3, a.average) for a in female] == [("ROU", Decimal("78.0"))]
