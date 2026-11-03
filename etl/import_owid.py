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
from etl.transform_owid import transform_owid_chart_file

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "owid"

SOURCE_NAME = "Our World in Data"
SOURCE_URL = "https://ourworldindata.org"

CHARTS = [
    # (code, name, unit, cache filename)
    (
        "OWID_LIFE_EXPECTANCY",
        "Life expectancy (OWID)",
        "years",
        "life-expectancy_full.csv",
    ),
]


def import_all() -> list[dict]:
    results: list[dict] = []
    with Session(get_engine()) as session:
        # The observation FK points at the country table, so that is the set
        # that counts (not the cached World Bank file).
        valid_iso3 = set(session.scalars(select(Country.iso3)))
        if not valid_iso3:
            results.append({
                "source": SOURCE_NAME, "item": "countries", "status": "failed",
                "message": "no countries in the database; load the World Bank countries first",
            })

            return results

        source_id = get_or_create_source(session, SOURCE_NAME, SOURCE_URL)
        session.commit()

        for code, name, unit, filename in CHARTS:
            path = RAW_DIR / filename
            if not path.exists():
                results.append({
                    "source": SOURCE_NAME, "item": code, "status": "skip",
                    "message": f"missing {path.name}",
                })
                continue

            try:
                raw = transform_owid_chart_file(path, code)
                cleaned = clean_observations(raw, valid_iso3)
                indicator_id = get_or_create_indicator(
                    session, code, name, unit, source_id
                )
                loaded = upsert_observations(session, cleaned, indicator_id)
                log_import(
                    session, SOURCE_NAME, code, read_source_url(path), loaded
                )
                session.commit()
                results.append({
                    "source": SOURCE_NAME, "item": code, "status": "ok",
                    "message": f"raw={len(raw)} clean={len(cleaned)} loaded={loaded}",
                })
            except (ValueError, OSError, SQLAlchemyError) as exc:
                session.rollback()
                logger.exception("%s: import failed", code)
                results.append({
                    "source": SOURCE_NAME, "item": code, "status": "failed",
                    "message": f"{type(exc).__name__}: {exc}",
                })

    return results


def main() -> None:
    results = import_all()
    for result in results:
        print(
            f"{result['source']:<18} {result['item']:<22} "
            f"{result['status']:<8} {result['message']}"
        )

    failed = [result["item"] for result in results if result["status"] == "failed"]
    if failed:
        raise SystemExit(f"{len(failed)} import(s) failed: {', '.join(failed)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    main()
