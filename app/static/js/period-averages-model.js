// Business logic (client): the page's defaults and selection rules.
// No DOM, no fetch.

export const DEFAULT_INDICATOR = "OWID_LIFE_EXPECTANCY";
export const DEFAULT_REGION = "Europe & Central Asia";
export const DEFAULT_COUNTRIES = ["ROU", "FRA", "DEU", "ITA", "POL"];
// One distinct color per line: the palette has 8, and more lines than that
// would no longer be told apart on the chart.
export const MAX_SELECTED_COUNTRIES = 8;

export function defaultIndicator(indicators) {
  const preferred = indicators.find((indicator) => indicator.code === DEFAULT_INDICATOR);
  return (preferred ?? indicators[0])?.code ?? null;
}

/** The default countries that exist in ``countries``, capped at the maximum. */
export function defaultSelection(countries) {
  const available = new Set(countries.map((country) => country.iso3));
  return DEFAULT_COUNTRIES.filter((iso3) => available.has(iso3)).slice(
    0,
    MAX_SELECTED_COUNTRIES,
  );
}

export function canSelectMore(selectedIso3s) {
  return selectedIso3s.length < MAX_SELECTED_COUNTRIES;
}
