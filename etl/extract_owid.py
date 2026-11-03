import csv
import io
from pathlib import Path

import requests

from etl.raw_files import save_raw

BASE_URL = "https://ourworldindata.org/grapher"
HTTP_TIMEOUT_S = 120
_HEADERS = {"User-Agent": "Our World In Data data fetch/1.0"}
_YEAR_COLUMN = "year"
_DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "owid"


def _chart_url(slug: str) -> str:
    return f"{BASE_URL}/{slug}.csv?v=1&csvType=full&useColumnShortNames=true"


def _download_csv(slug: str) -> tuple[bytes, str]:
    url = _chart_url(slug)
    response = requests.get(url, headers=_HEADERS, timeout=HTTP_TIMEOUT_S)
    response.raise_for_status()

    return response.content, url


def _lines_for_year(content: bytes, year: int, url: str) -> bytes:
    """Keep the header and the records for ``year``, byte-for-byte.

    The original lines are copied rather than re-serialized, so the subset is
    still raw data. ``line_num`` maps each record back to its source lines,
    which also handles quoted fields that span several lines.
    """
    lines = content.decode("utf-8-sig").splitlines(keepends=True)
    reader = csv.reader(lines)
    header = next(reader, None)
    if header is None or _YEAR_COLUMN not in header:
        raise ValueError(f"{url}: no {_YEAR_COLUMN!r} column (got {header})")
    year_index = header.index(_YEAR_COLUMN)

    kept = lines[: reader.line_num]
    start = reader.line_num
    for record in reader:
        if len(record) > year_index and record[year_index].strip() == str(year):
            kept.extend(lines[start : reader.line_num])
        start = reader.line_num

    return "".join(kept).encode("utf-8")


def download_owid_chart(
    slug: str,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    content, url = _download_csv(slug)
    path = save_raw(output_dir or _DEFAULT_RAW_DIR, f"{slug}_full.csv", content, url)

    return path, url


def download_owid_chart_for_year(
    slug: str,
    year: int,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    content, url = _download_csv(slug)
    path = save_raw(
        output_dir or _DEFAULT_RAW_DIR,
        f"{slug}_{year}.csv",
        _lines_for_year(content, year, url),
        url,
    )

    return path, url
