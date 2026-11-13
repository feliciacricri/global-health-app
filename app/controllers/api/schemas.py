"""JSON shapes of the REST API (pydantic), built from the service layer's types.

They are the API's public contract: renaming a field in a domain dataclass
must not silently change what clients receive. Averages are sent as JSON
numbers (pydantic would send a ``Decimal`` as a string) so a client can chart
them directly.
"""

from decimal import Decimal

from pydantic import BaseModel

from app.domain import IndicatorInfo, Option
from app.services.period_average_service import (
    CountrySeries,
    Period,
    PeriodAverageReport,
)


class CountryResponse(BaseModel):
    iso3: str
    name: str

    @classmethod
    def from_option(cls, option: Option) -> "CountryResponse":
        return cls(iso3=option.value, name=option.label)


class IndicatorResponse(BaseModel):
    code: str
    name: str

    @classmethod
    def from_option(cls, option: Option) -> "IndicatorResponse":
        return cls(code=option.value, name=option.label)


class IndicatorDetailResponse(BaseModel):
    code: str
    name: str
    unit: str | None

    @classmethod
    def from_domain(cls, indicator: IndicatorInfo) -> "IndicatorDetailResponse":
        return cls(code=indicator.code, name=indicator.name, unit=indicator.unit)


class PeriodResponse(BaseModel):
    start: int
    end: int
    label: str

    @classmethod
    def from_domain(cls, period: Period) -> "PeriodResponse":
        return cls(start=period.start, end=period.end, label=period.label)


class CountrySeriesResponse(BaseModel):
    country_iso3: str
    country_name: str
    averages: list[float | None]

    @classmethod
    def from_domain(cls, series: CountrySeries) -> "CountrySeriesResponse":
        return cls(
            country_iso3=series.country_iso3,
            country_name=series.country_name,
            averages=[_to_number(average) for average in series.averages],
        )


class PeriodAveragesResponse(BaseModel):
    indicator: IndicatorDetailResponse
    periods: list[PeriodResponse]
    series: list[CountrySeriesResponse]

    @classmethod
    def from_domain(cls, report: PeriodAverageReport) -> "PeriodAveragesResponse":
        return cls(
            indicator=IndicatorDetailResponse.from_domain(report.indicator),
            periods=[PeriodResponse.from_domain(p) for p in report.periods],
            series=[CountrySeriesResponse.from_domain(s) for s in report.series],
        )


def _to_number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
