import json
from pathlib import Path

import requests

from etl.json_types import JsonRecord
from etl.raw_files import save_raw

BASE_URL = "https://ghoapi.azureedge.net/api"
_DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "who"


class WhoApiError(RuntimeError):
    """The WHO GHO API returned a response we cannot interpret."""


def _download_rows(code: str, filter_expr: str) -> tuple[list[JsonRecord], str]:
    params: dict[str, str] | None = {"$filter": filter_expr}
    rows: list[JsonRecord] = []
    request_url: str | None = None
    next_url: str | None = f"{BASE_URL}/{code}"
    while next_url:
        response = requests.get(next_url, params=params, timeout=120)
        response.raise_for_status()
        # the first request's full URL (with $filter) identifies the data set
        request_url = request_url or response.url
        payload: object = response.json()
        if not isinstance(payload, dict):
            raise WhoApiError(f"{next_url}: expected a JSON object, got {payload!r}")
        value = payload.get("value", [])
        if not isinstance(value, list):
            raise WhoApiError(f"{next_url}: 'value' is not a list: {value!r}")
        rows.extend(value)
        next_link = payload.get("@odata.nextLink")
        next_url = next_link if isinstance(next_link, str) else None
        # nextLink already carries the $filter; don't resend it
        params = None

    assert request_url is not None  # the loop always runs at least once
    return rows, request_url


def download_who_indicator(
    code: str,
    year_from: int = 2000,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    rows, url = _download_rows(
        code, f"SpatialDimType eq 'COUNTRY' and TimeDim ge {year_from}"
    )
    path = save_raw(
        output_dir or _DEFAULT_RAW_DIR,
        f"{code}_from{year_from}.json",
        json.dumps(rows).encode("utf-8"),
        url,
    )

    return path, url


def download_who_indicator_for_year(
    code: str,
    year: int,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    rows, url = _download_rows(
        code, f"SpatialDimType eq 'COUNTRY' and TimeDim eq {year}"
    )
    path = save_raw(
        output_dir or _DEFAULT_RAW_DIR,
        f"{code}_{year}.json",
        json.dumps(rows).encode("utf-8"),
        url,
    )

    return path, url
