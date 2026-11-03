import logging

import requests
from sqlalchemy.exc import SQLAlchemyError

from etl.extract_owid import download_owid_chart
from etl.extract_who import WhoApiError, download_who_indicator
from etl.extract_worldbank import (
    WorldBankApiError,
    download_worldbank_countries,
    download_worldbank_indicator,
)
from etl.import_owid import import_all as owid_import_all
from etl.import_who import import_all as who_import_all
from etl.import_worldbank import import_all as wb_import_all

logger = logging.getLogger(__name__)

# Failures we expect from a download or a load; anything else is a bug and
# should crash loudly instead of becoming a "failed" row.
_EXTRACT_ERRORS = (
    requests.RequestException,
    WhoApiError,
    WorldBankApiError,
    OSError,
    ValueError,
)
_LOAD_ERRORS = (ValueError, OSError, SQLAlchemyError)

_WB_INDICATOR_CODES = (
    "SH.XPD.CHEX.GD.ZS",
    "SH.IMM.MEAS",
    "SP.DYN.IMRT.IN",
    "NY.GDP.PCAP.CD",
)
_OWID_SLUGS = ("life-expectancy",)
_WHO_INDICATOR_CODES = ("WHOSIS_000001",)


def _ok(source: str, item: str, message: str) -> dict:
    return {"source": source, "item": item, "status": "ok", "message": message}


def _failed(source: str, item: str, exc: Exception) -> dict:
    """Build a failed result; call from an ``except`` block (logs the traceback)."""
    logger.exception("%s %s failed", source, item)
    return {
        "source": source,
        "item": item,
        "status": "failed",
        "message": f"{type(exc).__name__}: {exc}",
    }


def extract_all() -> list[dict]:
    results: list[dict] = []

    try:
        path, _ = download_worldbank_countries()
        results.append(
            _ok("World Bank", "countries", f"{path.name} ({path.stat().st_size:,} bytes)")
        )
    except _EXTRACT_ERRORS as exc:
        results.append(_failed("World Bank", "countries", exc))

    for code in _WB_INDICATOR_CODES:
        try:
            path, _ = download_worldbank_indicator(code)
            results.append(
                _ok("World Bank", code, f"{path.name} ({path.stat().st_size:,} bytes)")
            )
        except _EXTRACT_ERRORS as exc:
            results.append(_failed("World Bank", code, exc))

    for slug in _OWID_SLUGS:
        try:
            path, _ = download_owid_chart(slug)
            results.append(
                _ok(
                    "Our World in Data",
                    slug,
                    f"{path.name} ({path.stat().st_size:,} bytes)",
                )
            )
        except _EXTRACT_ERRORS as exc:
            results.append(_failed("Our World in Data", slug, exc))

    for code in _WHO_INDICATOR_CODES:
        try:
            path, _ = download_who_indicator(code)
            results.append(
                _ok("WHO GHO", code, f"{path.name} ({path.stat().st_size:,} bytes)")
            )
        except _EXTRACT_ERRORS as exc:
            results.append(_failed("WHO GHO", code, exc))

    return results


def load_all() -> list[dict]:
    results: list[dict] = []
    for import_fn in (wb_import_all, owid_import_all, who_import_all):
        try:
            results.extend(import_fn())
        except _LOAD_ERRORS as exc:
            results.append(_failed("unknown", "import_all", exc))

    return results
