import logging

from sqlalchemy.orm import Session

from app.database import get_engine
from etl.import_runner import (
    IMPORT_ERRORS,
    RAW_ROOT,
    IndicatorSpec,
    SourceSpec,
    import_indicators,
    report_and_exit_on_failure,
)
from etl.load import upsert_countries
from etl.step_result import StepResult
from etl.transform_worldbank import (
    transform_worldbank_country_file,
    transform_worldbank_indicator_file,
)

logger = logging.getLogger(__name__)

SOURCE = SourceSpec(
    name="World Bank",
    url="https://data.worldbank.org",
    raw_dir=RAW_ROOT / "worldbank",
)
COUNTRIES_FILENAME = "countries.json"


def _indicator(code: str, name: str, unit: str) -> IndicatorSpec:
    # Matches the file name written by extract_worldbank's default year range.
    return IndicatorSpec(
        code=code,
        remote_id=code,
        name=name,
        unit=unit,
        raw_filename=f"{code}_2000-2023.json",
    )


INDICATORS = (
    _indicator("SH.XPD.CHEX.GD.ZS", "Current health expenditure", "% of GDP"),
    _indicator("SH.IMM.MEAS", "Measles immunization", "% of children 12-23 months"),
    _indicator("SP.DYN.IMRT.IN", "Infant mortality rate", "per 1,000 live births"),
    _indicator("NY.GDP.PCAP.CD", "GDP per capita", "current US$"),
)


def _import_countries(session: Session) -> tuple[StepResult, set[str]]:
    """Load the country dimension; return the result and the ISO3 codes loaded."""
    path = SOURCE.raw_dir / COUNTRIES_FILENAME
    if not path.exists():
        message = f"missing {path.name}; run Extract first"
        return StepResult.failed(SOURCE.name, "countries", message), set()

    try:
        countries = transform_worldbank_country_file(path)
        upsert_countries(session, countries)
        session.commit()
    except IMPORT_ERRORS as error:
        session.rollback()
        logger.exception("%s countries: import failed", SOURCE.name)
        return StepResult.from_error(SOURCE.name, "countries", error), set()

    message = f"{len(countries)} upserted"
    return StepResult.ok(SOURCE.name, "countries", message), set(countries["iso3"])


def import_all() -> list[StepResult]:
    with Session(get_engine()) as session:
        countries_result, known_countries = _import_countries(session)
        if not known_countries:
            return [countries_result]

        return [countries_result] + import_indicators(
            session,
            SOURCE,
            INDICATORS,
            transform_worldbank_indicator_file,
            known_countries,
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    report_and_exit_on_failure(import_all())
