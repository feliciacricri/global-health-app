from pathlib import Path

import pandas as pd

_NORMALIZED_COLUMNS = ["country_iso3", "indicator_code", "year", "sex", "value"]
_ID_COLUMNS = ("entity", "code", "year")


def transform_owid_chart(chart: pd.DataFrame, indicator_code: str) -> pd.DataFrame:
    if chart.empty:
        return pd.DataFrame(columns=_NORMALIZED_COLUMNS)

    # OWID chart CSVs (useColumnShortNames=true) are entity, code, year plus
    # exactly one value column whose name depends on the chart slug.
    missing = [column for column in _ID_COLUMNS if column not in chart.columns]
    value_columns = [column for column in chart.columns if column not in _ID_COLUMNS]
    if missing or len(value_columns) != 1:
        raise ValueError(
            f"unexpected OWID chart columns {list(chart.columns)}: need "
            f"{list(_ID_COLUMNS)} and exactly one value column"
        )

    return pd.DataFrame(
        {
            "country_iso3": chart["code"],
            "indicator_code": indicator_code,
            "year": chart["year"],
            "sex": None,
            "value": chart[value_columns[0]],
        }
    )


def transform_owid_chart_file(path: Path, indicator_code: str) -> pd.DataFrame:
    chart = pd.read_csv(path)

    return transform_owid_chart(chart, indicator_code)
