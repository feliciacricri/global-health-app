// Page controller (client): reacts to the filters, asks the API for data,
// lets the model shape it and the view draw it.

import {
  fetchCountries,
  fetchIndicators,
  fetchPeriodAverages,
  fetchRegions,
} from "./api-client.js";
import {
  ColorSlots,
  DEFAULT_PERIOD_YEARS,
  DEFAULT_REGION,
  FIRST_YEAR,
  LAST_YEAR,
  PERIOD_CHOICES,
  canSelectMore,
  countriesWithoutData,
  defaultIndicator,
  defaultSelection,
  toChart,
  toTable,
} from "./period-averages-model.js";
import { PeriodAveragesView } from "./period-averages-view.js";

class PeriodAveragesPage {
  constructor(view) {
    this.view = view;
    this.colorSlots = new ColorSlots(view.seriesColorCount);
    this.countries = [];
    this.selectedIso3s = [];
    this.report = null;
    this.pendingRequest = null;
  }

  async start() {
    const [indicators, regions] = await Promise.all([fetchIndicators(), fetchRegions()]);
    const region = regions.includes(DEFAULT_REGION) ? DEFAULT_REGION : "";
    this.view.renderIndicators(indicators, defaultIndicator(indicators));
    this.view.renderRegions(regions, region);
    this.view.renderPeriodChoices(PERIOD_CHOICES, DEFAULT_PERIOD_YEARS);

    this.countries = await fetchCountries(region);
    this.selectedIso3s = defaultSelection(this.countries);
    this.renderCountries();
    this.listen();
    await this.refresh();
  }

  listen() {
    const { view } = this;
    view.indicatorSelect.addEventListener("change", () => this.refresh());
    view.periodSelect.addEventListener("change", () => this.refresh());
    view.regionSelect.addEventListener("change", () => this.changeRegion());
    view.countryList.addEventListener("change", (event) => this.toggleCountry(event.target));
    // The chart's colors come from CSS, which has its own dark-mode values.
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", () => this.renderReport());
  }

  async changeRegion() {
    this.countries = await fetchCountries(this.view.regionSelect.value);
    // Keep the ticked countries that are in the new region.
    const inRegion = new Set(this.countries.map((country) => country.iso3));
    this.selectedIso3s = this.selectedIso3s.filter((iso3) => inRegion.has(iso3));
    this.renderCountries();
    await this.refresh();
  }

  async toggleCountry(checkbox) {
    this.selectedIso3s = checkbox.checked
      ? [...this.selectedIso3s, checkbox.value]
      : this.selectedIso3s.filter((iso3) => iso3 !== checkbox.value);
    this.renderCountries();
    await this.refresh();
  }

  renderCountries() {
    this.view.renderCountries(this.countries, this.selectedIso3s, canSelectMore(this.selectedIso3s));
  }

  async refresh() {
    // Only the answer to the latest filters may be drawn.
    this.pendingRequest?.abort();
    if (this.selectedIso3s.length === 0) {
      this.report = null;
      this.view.clearResults();
      this.view.showStatus("Choose at least one country.");
      return;
    }

    const request = new AbortController();
    this.pendingRequest = request;
    this.view.showStatus("Loading…");
    try {
      this.report = await fetchPeriodAverages(this.currentQuery(), request.signal);
    } catch (error) {
      if (error.name !== "AbortError") {
        this.report = null;
        this.view.clearResults();
        this.view.showStatus(`Could not load the data: ${error.message}`, { isError: true });
      }
      return;
    }
    this.colorSlots.update(this.selectedIso3s);
    this.renderReport();
  }

  currentQuery() {
    return {
      indicatorCode: this.view.indicatorSelect.value,
      countryIso3s: this.selectedIso3s,
      firstYear: FIRST_YEAR,
      lastYear: LAST_YEAR,
      periodYears: Number(this.view.periodSelect.value),
    };
  }

  renderReport() {
    if (this.report === null) {
      return;
    }
    this.view.renderTable(toTable(this.report));
    this.view.renderChart(toChart(this.report, this.colorSlots));
    const missing = countriesWithoutData(this.report, this.selectedIso3s, this.countries);
    this.view.showStatus(missing.length ? `No data for: ${missing.join(", ")}.` : "");
  }
}

const view = new PeriodAveragesView(document.querySelector("#period-averages"));
new PeriodAveragesPage(view).start().catch((error) => {
  view.showStatus(`Could not load the page: ${error.message}`, { isError: true });
});
