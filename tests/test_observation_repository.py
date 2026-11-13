"""Data access layer: queries against a seeded PostgreSQL schema."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.domain import ObservationCriteria, ObservationListItem, Option
from app.models import Sex
from app.repositories.observation_repository import ObservationRepository

ALL = ObservationCriteria()


@pytest.fixture
def repository(seeded: Session) -> ObservationRepository:
    return ObservationRepository(seeded)


def _keys(items: list[ObservationListItem]) -> list[tuple]:
    return [(i.country_iso3, i.indicator_code, i.year, i.sex) for i in items]


def test_find_returns_rows_in_stable_order(repository: ObservationRepository) -> None:
    items = repository.find(ALL, limit=100, offset=0)

    # country name, year desc, indicator code, sex
    assert _keys(items) == [
        ("FRA", "WHOSIS_000001", 2020, Sex.BOTH),
        ("FRA", "NY.GDP.PCAP.CD", 2015, Sex.BOTH),
        ("KEN", "WHOSIS_000001", 2020, Sex.BOTH),
        ("KEN", "NY.GDP.PCAP.CD", 2000, Sex.BOTH),
        ("ROU", "NY.GDP.PCAP.CD", 2020, Sex.BOTH),
        ("ROU", "WHOSIS_000001", 2020, Sex.BOTH),
        ("ROU", "WHOSIS_000001", 2020, Sex.FEMALE),
        ("ROU", "WHOSIS_000001", 2020, Sex.MALE),
        ("ROU", "WHOSIS_000001", 2010, Sex.BOTH),
    ]


def test_find_joins_country_and_indicator_details(
    repository: ObservationRepository,
) -> None:
    criteria = ObservationCriteria(country_iso3="FRA", year_from=2020)

    assert repository.find(criteria, limit=100, offset=0) == [
        ObservationListItem(
            country_name="France",
            country_iso3="FRA",
            region="Europe & Central Asia",
            indicator_code="WHOSIS_000001",
            indicator_name="Life expectancy at birth",
            unit="years",
            year=2020,
            sex=Sex.BOTH,
            value=Decimal("82.2000"),
        )
    ]


def test_missing_value_is_none(repository: ObservationRepository) -> None:
    criteria = ObservationCriteria(country_iso3="KEN", indicator_code="NY.GDP.PCAP.CD")

    assert [item.value for item in repository.find(criteria, limit=100, offset=0)] == [None]


@pytest.mark.parametrize(
    ("criteria", "expected_count"),
    [
        (ObservationCriteria(country_iso3="ROU"), 5),
        (ObservationCriteria(indicator_code="NY.GDP.PCAP.CD"), 3),
        (ObservationCriteria(region="Sub-Saharan Africa"), 2),
        (ObservationCriteria(year_from=2015), 7),
        (ObservationCriteria(year_to=2010), 2),
        (ObservationCriteria(country_iso3="ROU", year_from=2011, year_to=2020), 4),
        (ObservationCriteria(country_iso3="ROU", indicator_code="WHOSIS_000001",
                             year_to=2010), 1),
        (ObservationCriteria(country_iso3="XXX"), 0),
    ],
)
def test_filters_apply_to_find_and_count(
    repository: ObservationRepository,
    criteria: ObservationCriteria,
    expected_count: int,
) -> None:
    items = repository.find(criteria, limit=100, offset=0)

    assert len(items) == expected_count
    assert repository.count(criteria) == expected_count
    for item in items:
        if criteria.country_iso3 is not None:
            assert item.country_iso3 == criteria.country_iso3
        if criteria.indicator_code is not None:
            assert item.indicator_code == criteria.indicator_code
        if criteria.region is not None:
            assert item.region == criteria.region
        if criteria.year_from is not None:
            assert item.year >= criteria.year_from
        if criteria.year_to is not None:
            assert item.year <= criteria.year_to


def test_limit_and_offset_page_through_without_gaps_or_repeats(
    repository: ObservationRepository,
) -> None:
    everything = _keys(repository.find(ALL, limit=100, offset=0))

    pages = [_keys(repository.find(ALL, limit=4, offset=offset)) for offset in (0, 4, 8)]

    assert [len(page) for page in pages] == [4, 4, 1]
    assert [key for page in pages for key in page] == everything


def test_offset_past_the_end_returns_nothing(repository: ObservationRepository) -> None:
    assert repository.find(ALL, limit=10, offset=100) == []


def test_filter_lookups_are_sorted_by_label(repository: ObservationRepository) -> None:
    assert repository.list_countries() == (
        Option("FRA", "France"),
        Option("KEN", "Kenya"),
        Option("XKX", "Kosovo"),
        Option("ROU", "Romania"),
    )
    assert repository.list_indicators() == (
        Option("NY.GDP.PCAP.CD", "GDP per capita"),
        Option("WHOSIS_000001", "Life expectancy at birth"),
    )


def test_regions_are_distinct_and_skip_missing_ones(
    repository: ObservationRepository,
) -> None:
    assert repository.list_regions() == ("Europe & Central Asia", "Sub-Saharan Africa")


def test_countries_of_one_region(repository: ObservationRepository) -> None:
    assert repository.list_countries("Europe & Central Asia") == (
        Option("FRA", "France"),
        Option("ROU", "Romania"),
    )
    assert repository.list_countries("Antarctica") == ()
