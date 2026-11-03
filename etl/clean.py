import logging
from typing import NamedTuple

import pandas as pd

from app.models import Sex

logger = logging.getLogger(__name__)

_OUTPUT_COLUMNS = ["country_iso3", "indicator_code", "year", "sex", "value"]
_KEY_COLUMNS = ["country_iso3", "indicator_code", "year", "sex"]

# WHO GHO uses "SEX_BTSX" etc.; derived from the model so the two cannot drift.
_SEX_MAP = {f"SEX_{sex.value}": sex.value for sex in Sex}
_VALID_SEX = {sex.value for sex in Sex}


class _Bounds(NamedTuple):
    """Plausible value range; ``high`` is inclusive, ``low`` if ``low_inclusive``."""

    low: float
    high: float
    low_inclusive: bool = True


# Per-indicator plausibility bounds. Values outside them are dropped before
# reaching the database. A life expectancy or GDP per capita of exactly 0 is
# not a real measurement, so those lower bounds are exclusive.
_INDICATOR_BOUNDS = {
    "SH.XPD.CHEX.GD.ZS": _Bounds(0, 100),
    "SH.IMM.MEAS": _Bounds(0, 100),
    "SP.DYN.IMRT.IN": _Bounds(0, 1000),
    "NY.GDP.PCAP.CD": _Bounds(0, 500_000, low_inclusive=False),
    "WHOSIS_000001": _Bounds(0, 120, low_inclusive=False),
    "OWID_LIFE_EXPECTANCY": _Bounds(0, 120, low_inclusive=False),
}


def _drop(cleaned: pd.DataFrame, mask: pd.Series, reason: str) -> pd.DataFrame:
    """Drop the rows where ``mask`` is true, logging how many and why."""
    dropped = int(mask.sum())
    if dropped:
        logger.info("dropped %d observation rows: %s", dropped, reason)
    return cleaned[~mask]


def _out_of_bounds(cleaned: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=cleaned.index)
    for code, bounds in _INDICATOR_BOUNDS.items():
        value = cleaned["value"]
        too_low = value < bounds.low if bounds.low_inclusive else value <= bounds.low
        mask |= (cleaned["indicator_code"] == code) & (too_low | (value > bounds.high))
    return mask


def clean_observations(
    normalized: pd.DataFrame,
    valid_iso3: set[str],
    *,
    year_window: tuple[int, int] = (2000, 2024),
) -> pd.DataFrame:
    if normalized.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    cleaned = normalized.copy()

    cleaned["country_iso3"] = (
        cleaned["country_iso3"].astype("string").str.strip().str.upper()
    )
    cleaned = _drop(
        cleaned,
        ~cleaned["country_iso3"].isin(valid_iso3).fillna(False).astype(bool),
        "not a known country (aggregate, region or missing code)",
    )

    cleaned["year"] = pd.to_numeric(cleaned["year"], errors="coerce")
    cleaned["value"] = pd.to_numeric(cleaned["value"], errors="coerce")
    cleaned = _drop(
        cleaned,
        cleaned["year"].isna() | cleaned["value"].isna(),
        "missing or non-numeric year/value",
    )
    # astype(int) would truncate 2010.5 to 2010 and overwrite the real 2010 row.
    cleaned = _drop(cleaned, cleaned["year"] % 1 != 0, "year is not a whole number")
    cleaned["year"] = cleaned["year"].astype(int)

    year_low, year_high = year_window
    cleaned = _drop(
        cleaned,
        (cleaned["year"] < year_low) | (cleaned["year"] > year_high),
        f"year outside {year_low}-{year_high}",
    )

    cleaned["sex"] = cleaned["sex"].fillna(Sex.BOTH.value).replace(_SEX_MAP)
    cleaned = _drop(cleaned, ~cleaned["sex"].isin(_VALID_SEX), "unknown sex code")

    cleaned = _drop(cleaned, _out_of_bounds(cleaned), "value outside plausible bounds")

    cleaned = _drop(
        cleaned,
        cleaned.duplicated(subset=_KEY_COLUMNS, keep="last"),
        "duplicate (country, indicator, year, sex); kept the last",
    )

    return cleaned[_OUTPUT_COLUMNS]
