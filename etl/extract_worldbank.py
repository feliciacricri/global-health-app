import json
from pathlib import Path

import requests

from etl.json_types import JsonRecord
from etl.raw_files import save_raw

BASE_URL = "https://api.worldbank.org/v2"
_DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "worldbank"


class WorldBankApiError(RuntimeError):
    """The World Bank API returned an error or an unexpected response."""


def _get_all_pages(url: str, params: dict[str, str | int]) -> list[JsonRecord]:
    # World Bank wraps every response as [metadata, records]; walk every page.
    # Errors (e.g. an unknown indicator) come back as HTTP 200 with
    # [{"message": [...]}], so the shape has to be checked.
    page = 1
    records: list[JsonRecord] = []
    while True:
        response = requests.get(
            url, params={**params, "format": "json", "page": page}, timeout=60
        )
        response.raise_for_status()
        body: object = response.json()
        if not (isinstance(body, list) and len(body) == 2):
            raise WorldBankApiError(f"{url}: unexpected response {body!r}")
        meta, data = body
        if not isinstance(meta, dict) or "pages" not in meta:
            raise WorldBankApiError(f"{url}: missing page metadata in {meta!r}")
        if data is not None and not isinstance(data, list):
            raise WorldBankApiError(f"{url}: records are not a list: {data!r}")
        records.extend(data or [])
        if page >= int(meta["pages"]):
            return records
        page += 1


def _source_url(url: str, params: dict[str, str | int]) -> str:
    """The request URL with its query string, minus the per-page parameter."""
    return requests.Request(
        "GET", url, params={**params, "format": "json"}
    ).prepare().url or url


def _save_records(
    output_dir: Path,
    filename: str,
    records: list[JsonRecord],
    url: str,
    params: dict[str, str | int],
) -> Path:
    return save_raw(
        output_dir,
        filename,
        json.dumps(records).encode("utf-8"),
        _source_url(url, params),
    )


def download_worldbank_countries(*, output_dir: Path | None = None) -> tuple[Path, str]:
    url = f"{BASE_URL}/country"
    params: dict[str, str | int] = {"per_page": 400}
    records = _get_all_pages(url, params)
    path = _save_records(
        output_dir or _DEFAULT_RAW_DIR, "countries.json", records, url, params
    )

    return path, url


def download_worldbank_indicator(
    code: str,
    years: str = "2000:2023",
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    url = f"{BASE_URL}/country/all/indicator/{code}"
    params: dict[str, str | int] = {"date": years, "per_page": 10000}
    records = _get_all_pages(url, params)
    path = _save_records(
        output_dir or _DEFAULT_RAW_DIR,
        f"{code}_{years.replace(':', '-')}.json",
        records,
        url,
        params,
    )

    return path, url


def download_worldbank_indicator_for_year(
    code: str,
    year: int,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    url = f"{BASE_URL}/country/all/indicator/{code}"
    params: dict[str, str | int] = {"date": str(year), "per_page": 10000}
    records = _get_all_pages(url, params)
    path = _save_records(
        output_dir or _DEFAULT_RAW_DIR, f"{code}_{year}.json", records, url, params
    )

    return path, url
