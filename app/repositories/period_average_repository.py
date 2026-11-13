"""Data access layer: per-period averages of an indicator, computed in SQL."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import IndicatorInfo, PeriodAverage, PeriodAverageQuery
from app.models import Country, Indicator, Observation, Sex


class PeriodAverageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_indicator(self, code: str) -> IndicatorInfo | None:
        query = select(Indicator.code, Indicator.name, Indicator.unit).where(
            Indicator.code == code
        )
        row = self._session.execute(query).one_or_none()
        return IndicatorInfo(**row._mapping) if row is not None else None

    def average_by_period(
        self, query: PeriodAverageQuery, *, sex: Sex
    ) -> list[PeriodAverage]:
        """One average per country and period that has at least one value,
        ordered by country name, then period."""
        # Computed in a subquery and grouped outside it: Postgres cannot tell
        # that the same expression with fresh bound parameters in GROUP BY
        # is the one in SELECT.
        period_start = (
            query.first_year
            + (Observation.year - query.first_year)
            // query.period_years
            * query.period_years
        )
        bucketed = (
            select(
                Observation.country_iso3,
                period_start.label("period_start"),
                Observation.value,
            )
            .join(Indicator, Observation.indicator_id == Indicator.indicator_id)
            .where(
                Indicator.code == query.indicator_code,
                Observation.country_iso3.in_(query.country_iso3s),
                Observation.year.between(query.first_year, query.last_year),
                Observation.sex == sex,
                Observation.value.is_not(None),
            )
            .subquery()
        )
        averages = (
            select(
                Country.iso3.label("country_iso3"),
                Country.name.label("country_name"),
                bucketed.c.period_start,
                func.avg(bucketed.c.value).label("average"),
                func.count().label("observation_count"),
            )
            .join(Country, Country.iso3 == bucketed.c.country_iso3)
            .group_by(Country.iso3, Country.name, bucketed.c.period_start)
            .order_by(Country.name, bucketed.c.period_start)
        )
        return [
            PeriodAverage(**row) for row in self._session.execute(averages).mappings()
        ]
