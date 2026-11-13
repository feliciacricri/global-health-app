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
