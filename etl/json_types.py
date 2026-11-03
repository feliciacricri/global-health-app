"""Type aliases and loaders for JSON returned by the external data APIs."""

import json
from pathlib import Path

JsonRecord = dict[str, object]


def read_json_records(path: Path) -> list[JsonRecord]:
    """Load a cached raw file that must hold a JSON array of objects."""
    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array, got {type(data).__name__}")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: item {index} is not an object: {item!r}")
    return data


def require_keys(record: JsonRecord, keys: tuple[str, ...], where: str) -> None:
    """Raise a clear error if ``record`` is missing any of ``keys``."""
    missing = [key for key in keys if key not in record]
    if missing:
        raise ValueError(f"{where}: record is missing {missing}: {record!r}")
