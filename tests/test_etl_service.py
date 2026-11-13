"""Service layer: ETL orchestration, with stub jobs (no network, no database)."""

from pathlib import Path

import pytest
import requests
from sqlalchemy.exc import OperationalError

from app.services.etl_service import (
    EtlService,
    ExtractJob,
    ImportJob,
    StepResult,
    StepStatus,
)


def _raise(error: Exception):
    def run():
        raise error

    return run


def test_extract_reports_each_file_and_keeps_going_after_a_failure(
    tmp_path: Path,
) -> None:
    raw_file = tmp_path / "countries.json"
    raw_file.write_bytes(b"x" * 1234)
    service = EtlService(
        extract_jobs=[
            ExtractJob("World Bank", "countries", lambda: (raw_file, "https://example.org")),
            ExtractJob("WHO GHO", "WHOSIS_000001", _raise(requests.HTTPError("500"))),
            ExtractJob("World Bank", "countries again", lambda: (raw_file, "https://example.org")),
        ],
        import_jobs=[],
    )

    results = service.extract_all()

    assert results == [
        StepResult.ok("World Bank", "countries", "countries.json (1,234 bytes)"),
        StepResult.failed("WHO GHO", "WHOSIS_000001", "HTTPError: 500"),
        StepResult.ok("World Bank", "countries again", "countries.json (1,234 bytes)"),
    ]


def test_extract_lets_unexpected_errors_crash() -> None:
    service = EtlService(
        extract_jobs=[ExtractJob("World Bank", "countries", _raise(KeyError("bug")))],
        import_jobs=[],
    )

    with pytest.raises(KeyError):
        service.extract_all()


def test_transform_and_load_runs_sources_in_order_and_flattens_results() -> None:
    world_bank = [StepResult.ok("World Bank", "countries", "217 upserted")]
    who = [
        StepResult.ok("WHO GHO", "WHOSIS_000001", "loaded=10"),
        StepResult.skipped("WHO GHO", "OTHER", "missing OTHER.json"),
    ]
    service = EtlService(
        extract_jobs=[],
        import_jobs=[
            ImportJob("World Bank", lambda: world_bank),
            ImportJob("WHO GHO", lambda: who),
        ],
    )

    assert service.transform_and_load_all() == world_bank + who


def test_transform_and_load_turns_a_source_wide_failure_into_a_result() -> None:
    database_down = OperationalError("SELECT 1", {}, Exception("connection refused"))
    service = EtlService(
        extract_jobs=[],
        import_jobs=[
            ImportJob("World Bank", _raise(database_down)),
            ImportJob("WHO GHO", lambda: [StepResult.ok("WHO GHO", "x", "loaded=1")]),
        ],
    )

    results = service.transform_and_load_all()

    assert [(r.source, r.item, r.status) for r in results] == [
        ("World Bank", "import", StepStatus.FAILED),
        ("WHO GHO", "x", StepStatus.OK),
    ]
    assert results[0].message.startswith("OperationalError:")


def test_default_jobs_cover_every_configured_indicator() -> None:
    service = EtlService()

    items = [(job.source, job.item) for job in service._extract_jobs]

    assert items == [
        ("World Bank", "countries"),
        ("World Bank", "SH.XPD.CHEX.GD.ZS"),
        ("World Bank", "SH.IMM.MEAS"),
        ("World Bank", "SP.DYN.IMRT.IN"),
        ("World Bank", "NY.GDP.PCAP.CD"),
        ("Our World in Data", "life-expectancy"),
        ("WHO GHO", "WHOSIS_000001"),
    ]
