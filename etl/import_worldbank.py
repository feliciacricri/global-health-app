import logging
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_engine
from etl.clean import clean_observations
from etl.load import (
    get_or_create_indicator,
    get_or_create_source,
    log_import,
    upsert_countries,
    upsert_observations,
)
from etl.raw_files import read_source_url
from etl.transform_worldbank import (
    transform_worldbank_country_file,
    transform_worldbank_indicator_file,
)

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "worldbank"
SOURCE_NAME = "World Bank"
SOURCE_URL = "https://data.worldbank.org"

INDICATORS = [
    # (code, name, unit, cache filename)
    (
        "SH.XPD.CHEX.GD.ZS",
        "Current health expenditure",
        "% of GDP",
        "SH.XPD.CHEX.GD.ZS_2000-2023.json",
    ),
    (
        "SH.IMM.MEAS",
        "Measles immunization",
        "% of children 12-23 months",
        "SH.IMM.MEAS_2000-2023.json",
    ),
    (
        "SP.DYN.IMRT.IN",
        "Infant mortality rate",
        "per 1,000 live births",
        "SP.DYN.IMRT.IN_2000-2023.json",
    ),
    (
        "NY.GDP.PCAP.CD",
        "GDP per capita",
        "current US$",
        "NY.GDP.PCAP.CD_2000-2023.json",
    ),
]


def main() -> None:
    failed: list[str] = []
    with Session(get_engine()) as session:
        countries = transform_worldbank_country_file(RAW_DIR / "countries.json")
        upsert_countries(session, countries)
        session.commit()
        print(f"countries: {len(countries)} upserted")

        valid_iso3 = set(countries["iso3"])
        source_id = get_or_create_source(session, SOURCE_NAME, SOURCE_URL)
        session.commit()

        for code, name, unit, filename in INDICATORS:
            path = RAW_DIR / filename
            if not path.exists():
                print(f"{code:<22} SKIP (missing {path.name})")
                continue

            try:
                raw = transform_worldbank_indicator_file(path, code)
                cleaned = clean_observations(raw, valid_iso3)
                indicator_id = get_or_create_indicator(
                    session, code, name, unit, source_id
                )
                loaded = upsert_observations(session, cleaned, indicator_id)
                log_import(
                    session, SOURCE_NAME, code, read_source_url(path), loaded
                )
                session.commit()
                print(
                    f"{code:<22} raw={len(raw):>6}  "
                    f"clean={len(cleaned):>6}  loaded={loaded:>6}"
                )
            except (ValueError, OSError, SQLAlchemyError):
                session.rollback()
                logger.exception("%s: import failed", code)
                failed.append(code)

    if failed:
        raise SystemExit(f"{len(failed)} import(s) failed: {', '.join(failed)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    main()
