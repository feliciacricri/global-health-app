import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Country
from etl.clean import clean_observations
from etl.load import (
    get_or_create_indicator,
    get_or_create_source,
    log_import,
    upsert_observations,
)
from etl.raw_files import read_source_url
from etl.transform_who import transform_who_file

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "who"

SOURCE_NAME = "WHO GHO"
SOURCE_URL = "https://www.who.int/data/gho"

INDICATORS = [
    # (code, name, unit, cache filename)
    (
        "WHOSIS_000001",
        "Life expectancy at birth",
        "years",
        "WHOSIS_000001_from2000.json",
    ),
]


def main() -> None:
    failed: list[str] = []
    with Session(get_engine()) as session:
        # The observation FK points at the country table, so that is the set
        # that counts (not the cached World Bank file).
        valid_iso3 = set(session.scalars(select(Country.iso3)))
        if not valid_iso3:
            raise SystemExit(
                "no countries in the database; "
                "run `python -m etl.import_worldbank` first"
            )
        source_id = get_or_create_source(session, SOURCE_NAME, SOURCE_URL)
        session.commit()

        for code, name, unit, filename in INDICATORS:
            path = RAW_DIR / filename
            if not path.exists():
                print(f"{code:<22} SKIP (missing {path.name})")
                continue

            try:
                raw = transform_who_file(path, code)
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
