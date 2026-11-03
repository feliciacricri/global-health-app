from pathlib import Path

import pandas as pd

from etl.json_types import JsonRecord, read_json_records, require_keys

_OBSERVATION_COLUMNS = ["country_iso3", "indicator_code", "year", "sex", "value"]
_COUNTRY_COLUMNS = ["iso3", "iso2", "name", "region", "income_group"]
_OBSERVATION_KEYS = ("countryiso3code", "date", "value")
_COUNTRY_KEYS = ("id", "iso2Code", "name", "region", "incomeLevel")


def _text(record: JsonRecord, key: str) -> str:
    value = record[key]
    if not isinstance(value, str):
        raise ValueError(f"World Bank {key!r} is not a string: {record!r}")
    return value.strip()


def _nested_text(record: JsonRecord, key: str) -> str:
    # e.g. "region": {"id": "LCN", "iso2code": "ZJ", "value": "Latin America ..."}
    value = record[key]
    if not isinstance(value, dict):
        raise ValueError(f"World Bank {key!r} is not an object: {record!r}")
    return _text(value, "value")


def transform_worldbank_indicator_records(
    records: list[JsonRecord], code: str
) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=_OBSERVATION_COLUMNS)

    for r in records:
        require_keys(r, _OBSERVATION_KEYS, f"World Bank {code}")

    return pd.DataFrame(
        {
            "country_iso3": [r["countryiso3code"] for r in records],
            "indicator_code": code,
            "year": [r["date"] for r in records],
            "sex": None,
            "value": [r["value"] for r in records],
        }
    )


def transform_worldbank_indicator_file(path: Path, code: str) -> pd.DataFrame:
    records = read_json_records(path)

    return transform_worldbank_indicator_records(records, code)


def transform_worldbank_country_records(records: list[JsonRecord]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=_COUNTRY_COLUMNS)

    for c in records:
        require_keys(c, _COUNTRY_KEYS, "World Bank country")

    # regional and income aggregates all share the "Aggregates" region value
    return pd.DataFrame(
        [
            {
                "iso3": _text(c, "id"),
                "iso2": _text(c, "iso2Code"),
                "name": _text(c, "name"),
                "region": _nested_text(c, "region"),
                "income_group": _nested_text(c, "incomeLevel"),
            }
            for c in records
            if _nested_text(c, "region") != "Aggregates"
        ]
    )


def transform_worldbank_country_file(path: Path) -> pd.DataFrame:
    records = read_json_records(path)

    return transform_worldbank_country_records(records)
