// Business logic (client): the page's defaults and selection rules, and the
// shaping of an API report into table rows and chart series. No DOM, no fetch.

export const DEFAULT_INDICATOR = "OWID_LIFE_EXPECTANCY";
export const DEFAULT_REGION = "Europe & Central Asia";
export const DEFAULT_COUNTRIES = ["ROU", "FRA", "DEU", "ITA", "POL"];
export const FIRST_YEAR = 2000;
export const LAST_YEAR = 2023;
export const PERIOD_CHOICES = [1, 2, 5, 10];
export const DEFAULT_PERIOD_YEARS = 5;
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

/**
 * Gives each selected country one of ``slotCount`` color slots and keeps it
 * while the country stays selected, so ticking another country never
 * repaints the lines already on the chart.
 */
export class ColorSlots {
  constructor(slotCount) {
    this.slotCount = slotCount;
    this.slotByIso3 = new Map();
  }

  /** Frees the slots of unselected countries and assigns the new ones. */
  update(selectedIso3s) {
    const selected = new Set(selectedIso3s);
    for (const iso3 of [...this.slotByIso3.keys()]) {
      if (!selected.has(iso3)) {
        this.slotByIso3.delete(iso3);
      }
    }
    for (const iso3 of selectedIso3s) {
      if (!this.slotByIso3.has(iso3)) {
        this.slotByIso3.set(iso3, this.firstFreeSlot());
      }
    }
  }

  slotOf(iso3) {
    return this.slotByIso3.get(iso3);
  }

  firstFreeSlot() {
    const used = new Set(this.slotByIso3.values());
    for (let slot = 0; slot < this.slotCount; slot += 1) {
      if (!used.has(slot)) {
        return slot;
      }
    }
    throw new Error(`more than ${this.slotCount} countries selected`);
  }
}

export function axisTitle(indicator) {
  return indicator.unit ? `${indicator.name} (${indicator.unit})` : indicator.name;
}

/** Table: one row per country, one cell per period (null where no data). */
export function toTable(report) {
  return {
    columns: report.periods.map((period) => period.label),
    rows: report.series.map((series) => ({
      label: `${series.country_name} (${series.country_iso3})`,
      cells: series.averages,
    })),
  };
}

/** Chart: the period labels on the x axis, one line per country. */
export function toChart(report, colorSlots) {
  return {
    labels: report.periods.map((period) => period.label),
    yTitle: axisTitle(report.indicator),
    lines: report.series.map((series) => ({
      label: series.country_name,
      values: series.averages,
      colorSlot: colorSlots.slotOf(series.country_iso3),
    })),
  };
}

/** Countries that were asked for but have no data for the indicator. */
export function countriesWithoutData(report, selectedIso3s, countries) {
  const withData = new Set(report.series.map((series) => series.country_iso3));
  return countries
    .filter((country) => selectedIso3s.includes(country.iso3) && !withData.has(country.iso3))
    .map((country) => country.name);
}
