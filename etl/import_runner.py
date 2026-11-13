"""Shared Transform & Load loop used by the per-source import scripts."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
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
from etl.step_result import StepResult, StepStatus

logger = logging.getLogger(__name__)

# Failures expected while reading a raw file or writing it to the database.
# Anything else is a bug and should crash instead of becoming a result row.
IMPORT_ERRORS = (ValueError, OSError, SQLAlchemyError)

RAW_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw"

TransformFile = Callable[[Path, str], pd.DataFrame]


@dataclass(frozen=True)
class SourceSpec:
    name: str
    url: str
    raw_dir: Path


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    """Code stored in the indicator table."""
    remote_id: str
    """Identifier at the source: its indicator code, or the OWID chart slug."""
    name: str
    unit: str
    raw_filename: str


def import_for_loaded_countries(
    source: SourceSpec,
    indicators: Iterable[IndicatorSpec],
    transform: TransformFile,
) -> list[StepResult]:
    """Import a source whose observations refer to already-loaded countries.

    The observation FK points at the country table, so the countries in the
    database (loaded from the World Bank) decide which rows are kept.
    """
    with Session(get_engine()) as session:
        known_countries = set(session.scalars(select(Country.iso3)))
        if not known_countries:
            return [
                StepResult.failed(
                    source.name,
                    "countries",
                    "no countries in the database; load the World Bank countries first",
                )
            ]

        return import_indicators(
            session, source, indicators, transform, known_countries
        )


def import_indicators(
    session: Session,
    source: SourceSpec,
    indicators: Iterable[IndicatorSpec],
    transform: TransformFile,
    known_countries: set[str],
) -> list[StepResult]:
    """Transform, clean and load each indicator, one transaction per indicator."""
    source_id = get_or_create_source(session, source.name, source.url)
    session.commit()

    return [
        _import_indicator(session, source, source_id, spec, transform, known_countries)
        for spec in indicators
    ]


def _import_indicator(
    session: Session,
    source: SourceSpec,
    source_id: int,
    spec: IndicatorSpec,
    transform: TransformFile,
    known_countries: set[str],
) -> StepResult:
    path = source.raw_dir / spec.raw_filename
    if not path.exists():
        return StepResult.skipped(source.name, spec.code, f"missing {path.name}")

    try:
        normalized = transform(path, spec.code)
        cleaned = clean_observations(normalized, known_countries)
        indicator_id = get_or_create_indicator(
            session, spec.code, spec.name, spec.unit, source_id
        )
        loaded = upsert_observations(session, cleaned, indicator_id)
        log_import(session, source.name, spec.code, read_source_url(path), loaded)
        session.commit()
    except IMPORT_ERRORS as error:
        session.rollback()
        logger.exception("%s %s: import failed", source.name, spec.code)
        return StepResult.from_error(source.name, spec.code, error)

    return StepResult.ok(
        source.name,
        spec.code,
        f"raw={len(normalized)} clean={len(cleaned)} loaded={loaded}",
    )


def report_and_exit_on_failure(results: Iterable[StepResult]) -> None:
    """Command-line output for the import scripts; exit non-zero on failures."""
    failed = []
    for result in results:
        print(f"{result.source:<18} {result.item:<22} {result.status:<8} {result.message}")
        if result.status is StepStatus.FAILED:
            failed.append(result.item)

    if failed:
        raise SystemExit(f"{len(failed)} import(s) failed: {', '.join(failed)}")
