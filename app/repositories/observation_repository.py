"""Data access layer: the only place the web app queries observations."""

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.domain import ObservationCriteria, ObservationListItem, Option
from app.models import Country, Indicator, Observation

# country/year alone has ties (several indicators and sexes per country-year);
# with LIMIT/OFFSET, Postgres may order ties differently per query, so rows
# could repeat or vanish between pages. The trailing PK makes it total.
_STABLE_ORDER = (
    Country.name,
    Observation.year.desc(),
    Indicator.code,
    Observation.sex,
    Observation.observation_id,
)


class ObservationRepository:
    """Reads observations and the lookup values used to filter them."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find(
        self, criteria: ObservationCriteria, *, limit: int, offset: int
    ) -> list[ObservationListItem]:
        query = (
            _matching_observations(criteria)
            .order_by(*_STABLE_ORDER)
            .limit(limit)
            .offset(offset)
        )
        return [
            ObservationListItem(**row)
            for row in self._session.execute(query).mappings()
        ]

    def count(self, criteria: ObservationCriteria) -> int:
        query = select(func.count()).select_from(
            _matching_observations(criteria).subquery()
        )
        return self._session.scalar(query) or 0

    def list_countries(self) -> tuple[Option, ...]:
        query = select(Country.iso3, Country.name).order_by(Country.name)
        return tuple(
            Option(value=iso3, label=name)
            for iso3, name in self._session.execute(query)
        )

    def list_indicators(self) -> tuple[Option, ...]:
        query = select(Indicator.code, Indicator.name).order_by(Indicator.name)
        return tuple(
            Option(value=code, label=name)
            for code, name in self._session.execute(query)
        )

    def list_regions(self) -> tuple[str, ...]:
        query = (
            select(Country.region)
            .where(Country.region.is_not(None))
            .distinct()
            .order_by(Country.region)
        )
        return tuple(self._session.scalars(query))


def _matching_observations(criteria: ObservationCriteria) -> Select:
    """Observations joined to their country and indicator, filtered."""
    return (
        select(
            Country.name.label("country_name"),
            Country.iso3.label("country_iso3"),
            Country.region,
            Indicator.code.label("indicator_code"),
            Indicator.name.label("indicator_name"),
            Indicator.unit,
            Observation.year,
            Observation.sex,
            Observation.value,
        )
        .join(Country, Observation.country_iso3 == Country.iso3)
        .join(Indicator, Observation.indicator_id == Indicator.indicator_id)
        .where(*_conditions(criteria))
    )


def _conditions(criteria: ObservationCriteria) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if criteria.country_iso3 is not None:
        conditions.append(Country.iso3 == criteria.country_iso3)
    if criteria.indicator_code is not None:
        conditions.append(Indicator.code == criteria.indicator_code)
    if criteria.region is not None:
        conditions.append(Country.region == criteria.region)
    if criteria.year_from is not None:
        conditions.append(Observation.year >= criteria.year_from)
    if criteria.year_to is not None:
        conditions.append(Observation.year <= criteria.year_to)
    return conditions
