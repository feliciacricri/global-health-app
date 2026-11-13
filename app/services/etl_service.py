"""Service layer for the ETL actions: Extract, and Transform & Load."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import requests

from etl import import_owid, import_who, import_worldbank
from etl.extract_owid import download_owid_chart
from etl.extract_who import WhoApiError, download_who_indicator
from etl.extract_worldbank import (
    WorldBankApiError,
    download_worldbank_countries,
    download_worldbank_indicator,
)
from etl.import_runner import IMPORT_ERRORS, IndicatorSpec, SourceSpec
from etl.step_result import StepResult, StepStatus

__all__ = ["EtlService", "ExtractJob", "ImportJob", "StepResult", "StepStatus"]

logger = logging.getLogger(__name__)

# Failures expected from a download. Anything else is a bug and should crash
# loudly instead of becoming a "failed" row.
EXTRACT_ERRORS = (
    requests.RequestException,
    WhoApiError,
    WorldBankApiError,
    OSError,
    ValueError,
)


@dataclass(frozen=True)
class ExtractJob:
    source: str
    item: str
    download: Callable[[], tuple[Path, str]]
    """Saves one raw file and returns (path, source URL)."""


@dataclass(frozen=True)
class ImportJob:
    source: str
    run: Callable[[], list[StepResult]]


def _download_jobs(
    source: SourceSpec,
    indicators: Sequence[IndicatorSpec],
    download: Callable[[str], tuple[Path, str]],
) -> list[ExtractJob]:
    return [
        ExtractJob(source.name, spec.remote_id, partial(download, spec.remote_id))
        for spec in indicators
    ]


def _default_extract_jobs() -> tuple[ExtractJob, ...]:
    # Built from the import scripts' indicator lists, so Extract downloads
    # exactly what Transform & Load reads.
    countries = ExtractJob(
        import_worldbank.SOURCE.name, "countries", download_worldbank_countries
    )
    return (
        countries,
        *_download_jobs(
            import_worldbank.SOURCE,
            import_worldbank.INDICATORS,
            download_worldbank_indicator,
        ),
        *_download_jobs(import_owid.SOURCE, import_owid.INDICATORS, download_owid_chart),
        *_download_jobs(import_who.SOURCE, import_who.INDICATORS, download_who_indicator),
    )


# World Bank goes first: it loads the countries the other sources refer to.
DEFAULT_IMPORT_JOBS = (
    ImportJob(import_worldbank.SOURCE.name, import_worldbank.import_all),
    ImportJob(import_owid.SOURCE.name, import_owid.import_all),
    ImportJob(import_who.SOURCE.name, import_who.import_all),
)


class EtlService:
    def __init__(
        self,
        extract_jobs: Sequence[ExtractJob] | None = None,
        import_jobs: Sequence[ImportJob] = DEFAULT_IMPORT_JOBS,
    ) -> None:
        self._extract_jobs = (
            _default_extract_jobs() if extract_jobs is None else tuple(extract_jobs)
        )
        self._import_jobs = tuple(import_jobs)

    def extract_all(self) -> list[StepResult]:
        """Download every source into data/raw/; one result per file."""
        return [_run_extract(job) for job in self._extract_jobs]

    def transform_and_load_all(self) -> list[StepResult]:
        """Transform, clean and load the raw files of every source."""
        return [result for job in self._import_jobs for result in _run_import(job)]


def _run_extract(job: ExtractJob) -> StepResult:
    try:
        path, _ = job.download()
    except EXTRACT_ERRORS as error:
        logger.exception("%s %s: extract failed", job.source, job.item)
        return StepResult.from_error(job.source, job.item, error)

    size = path.stat().st_size
    return StepResult.ok(job.source, job.item, f"{path.name} ({size:,} bytes)")


def _run_import(job: ImportJob) -> list[StepResult]:
    # Per-indicator failures come back as results; this catches failures of
    # the source as a whole, e.g. the database being unreachable.
    try:
        return job.run()
    except IMPORT_ERRORS as error:
        logger.exception("%s: import failed", job.source)
        return [StepResult.from_error(job.source, "import", error)]
