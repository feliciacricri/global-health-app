"""Service layer: averages of an indicator per period of years, per country.

Example: life expectancy averaged over 2000-2004, 2005-2009, ... for a few
European countries, laid out so a client can draw it as a table or a chart.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain import IndicatorInfo, PeriodAverage, PeriodAverageQuery
from app.models import Sex
from app.repositories.period_average_repository import PeriodAverageRepository

# The years this project covers ("2000-2023").
DEFAULT_FIRST_YEAR = 2000
DEFAULT_LAST_YEAR = 2023
DEFAULT_PERIOD_YEARS = 5
# Keeps a chart readable and a request cheap.
MAX_COUNTRIES = 20
AVERAGE_PRECISION = Decimal("0.01")
# Averages mix only the both-sexes values, never male and female rows with them.
AVERAGED_SEX = Sex.BOTH


class UnknownIndicatorError(LookupError):
    """No indicator has the requested code."""


class InvalidQueryError(ValueError):
    """The query cannot be answered as asked (e.g. the years are reversed)."""


@dataclass(frozen=True)
class Period:
    start: int
    end: int

    @property
    def label(self) -> str:
        return str(self.start) if self.start == self.end else f"{self.start}–{self.end}"


@dataclass(frozen=True)
class CountrySeries:
    """One country's averages, one per report period; ``None`` where the
    country has no values in that period."""

    country_iso3: str
    country_name: str
    averages: tuple[Decimal | None, ...]


@dataclass(frozen=True)
class PeriodAverageReport:
    indicator: IndicatorInfo
    periods: tuple[Period, ...]
    series: tuple[CountrySeries, ...]


class PeriodAverageService:
    def __init__(self, repository: PeriodAverageRepository) -> None:
        self._repository = repository

    def get_report(self, query: PeriodAverageQuery) -> PeriodAverageReport:
        """Averages per period for the countries in ``query`` that have data,
        sorted by country name.

        Raises InvalidQueryError or UnknownIndicatorError.
        """
        _validate(query)
        indicator = self._repository.find_indicator(query.indicator_code)
        if indicator is None:
            raise UnknownIndicatorError(f"unknown indicator {query.indicator_code!r}")

        periods = _periods(query)
        averages = self._repository.average_by_period(query, sex=AVERAGED_SEX)
        return PeriodAverageReport(
            indicator=indicator, periods=periods, series=_series(periods, averages)
        )


def _validate(query: PeriodAverageQuery) -> None:
    if query.period_years < 1:
        raise InvalidQueryError(
            f"period_years must be at least 1, got {query.period_years}"
        )
    if query.first_year > query.last_year:
        raise InvalidQueryError(
            f"first_year {query.first_year} is after last_year {query.last_year}"
        )
    if len(query.country_iso3s) > MAX_COUNTRIES:
        raise InvalidQueryError(
            f"at most {MAX_COUNTRIES} countries, got {len(query.country_iso3s)}"
        )


def _periods(query: PeriodAverageQuery) -> tuple[Period, ...]:
    return tuple(
        Period(start, min(start + query.period_years - 1, query.last_year))
        for start in range(query.first_year, query.last_year + 1, query.period_years)
    )


def _series(
    periods: tuple[Period, ...], averages: list[PeriodAverage]
) -> tuple[CountrySeries, ...]:
    """Pivots the (country, period) rows into one series per country, keeping
    the repository's country order."""
    names: dict[str, str] = {}
    by_country: dict[str, dict[int, Decimal]] = {}
    for row in averages:
        names[row.country_iso3] = row.country_name
        by_country.setdefault(row.country_iso3, {})[row.period_start] = row.average

    return tuple(
        CountrySeries(
            country_iso3=iso3,
            country_name=names[iso3],
            averages=tuple(_rounded(values.get(period.start)) for period in periods),
        )
        for iso3, values in by_country.items()
    )


def _rounded(average: Decimal | None) -> Decimal | None:
    if average is None:
        return None
    # Half up, as people round by hand (Decimal defaults to half even).
    return average.quantize(AVERAGE_PRECISION, rounding=ROUND_HALF_UP)
