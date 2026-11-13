"""Plain data types passed between the repository, service and controller layers.

They keep SQLAlchemy rows out of the services and templates, and HTTP request
objects out of the services and repositories.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.models import Sex


@dataclass(frozen=True)
class ObservationCriteria:
    """Filters for observations; ``None`` means "do not filter on this"."""

    country_iso3: str | None = None
    indicator_code: str | None = None
    region: str | None = None
    year_from: int | None = None
    year_to: int | None = None


@dataclass(frozen=True)
class ObservationListItem:
    """One entry of the observations list: an observation joined with its
    country and indicator details, ready to show."""

    country_name: str
    country_iso3: str
    region: str | None
    indicator_code: str
    indicator_name: str
    unit: str | None
    year: int
    sex: Sex
    value: Decimal | None


@dataclass(frozen=True)
class Option:
    """One choice in a filter drop-down."""

    value: str
    label: str


@dataclass(frozen=True)
class FilterOptions:
    countries: tuple[Option, ...]
    indicators: tuple[Option, ...]
    regions: tuple[str, ...]


@dataclass(frozen=True)
class IndicatorInfo:
    code: str
    name: str
    unit: str | None


@dataclass(frozen=True)
class PeriodAverageQuery:
    """Which values to average: one indicator, some countries, a year range
    split into periods of ``period_years`` (the last one may be shorter)."""

    indicator_code: str
    country_iso3s: tuple[str, ...]
    first_year: int
    last_year: int
    period_years: int


@dataclass(frozen=True)
class PeriodAverage:
    """The average of one country's values over the period starting at
    ``period_start``, as computed by the database."""

    country_iso3: str
    country_name: str
    period_start: int
    average: Decimal
    observation_count: int
