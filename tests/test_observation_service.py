"""Service layer: paging rules, with an in-memory repository (no database)."""

from decimal import Decimal

import pytest

from app.domain import FilterOptions, ObservationCriteria, ObservationListItem, Option
from app.models import Sex
from app.services.observation_service import ObservationPage, ObservationService


def _item(year: int) -> ObservationListItem:
    return ObservationListItem(
        country_name="Romania",
        country_iso3="ROU",
        region="Europe & Central Asia",
        indicator_code="WHOSIS_000001",
        indicator_name="Life expectancy at birth",
        unit="years",
        year=year,
        sex=Sex.BOTH,
        value=Decimal("74.2"),
    )


class FakeRepository:
    """Holds list items in memory and records the queries it receives."""

    def __init__(self, total_items: int) -> None:
        self.items = [_item(2000 + index) for index in range(total_items)]
        self.find_calls: list[tuple[ObservationCriteria, int, int]] = []

    def find(
        self, criteria: ObservationCriteria, *, limit: int, offset: int
    ) -> list[ObservationListItem]:
        self.find_calls.append((criteria, limit, offset))
        return self.items[offset : offset + limit]

    def count(self, criteria: ObservationCriteria) -> int:
        return len(self.items)

    def list_countries(self) -> tuple[Option, ...]:
        return (Option("ROU", "Romania"),)

    def list_indicators(self) -> tuple[Option, ...]:
        return (Option("WHOSIS_000001", "Life expectancy at birth"),)

    def list_regions(self) -> tuple[str, ...]:
        return ("Europe & Central Asia",)


def _service(total_items: int, page_size: int = 4) -> tuple[ObservationService, FakeRepository]:
    repository = FakeRepository(total_items)
    return ObservationService(repository, page_size=page_size), repository


@pytest.mark.parametrize(
    ("number", "expected_offset", "expected_years"),
    [(1, 0, [2000, 2001, 2002, 2003]), (2, 4, [2004, 2005, 2006, 2007]), (3, 8, [2008])],
)
def test_get_page_asks_the_repository_for_one_page(
    number: int, expected_offset: int, expected_years: list[int]
) -> None:
    service, repository = _service(total_items=9)
    criteria = ObservationCriteria(country_iso3="ROU")

    page = service.get_page(criteria, number)

    assert repository.find_calls == [(criteria, 4, expected_offset)]
    assert [item.year for item in page.items] == expected_years
    assert (page.number, page.size, page.total_items) == (number, 4, 9)


@pytest.mark.parametrize(
    ("total_items", "number", "total_pages", "has_previous", "has_next"),
    [
        (0, 1, 1, False, False),
        (4, 1, 1, False, False),
        (5, 1, 2, False, True),
        (9, 2, 3, True, True),
        (9, 3, 3, True, False),
        (9, 7, 3, True, False),
    ],
)
def test_page_navigation(
    total_items: int, number: int, total_pages: int, has_previous: bool, has_next: bool
) -> None:
    page = ObservationPage(items=[], number=number, size=4, total_items=total_items)

    assert page.total_pages == total_pages
    assert page.has_previous is has_previous
    assert page.has_next is has_next


def test_page_numbers_start_at_one() -> None:
    service, _ = _service(total_items=9)

    with pytest.raises(ValueError, match="start at 1"):
        service.get_page(ObservationCriteria(), 0)


def test_page_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="page_size"):
        ObservationService(FakeRepository(0), page_size=0)


def test_filter_options_come_from_the_repository() -> None:
    service, _ = _service(total_items=0)

    assert service.get_filter_options() == FilterOptions(
        countries=(Option("ROU", "Romania"),),
        indicators=(Option("WHOSIS_000001", "Life expectancy at birth"),),
        regions=("Europe & Central Asia",),
    )
