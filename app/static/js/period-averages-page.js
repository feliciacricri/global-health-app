// Page controller (client): fills the filters from the API and reacts to
// them, connecting the data access, model and view modules.

import { fetchCountries, fetchIndicators, fetchRegions } from "./api-client.js";
import {
  DEFAULT_REGION,
  canSelectMore,
  defaultIndicator,
  defaultSelection,
} from "./period-averages-model.js";
import { PeriodAveragesView } from "./period-averages-view.js";

class PeriodAveragesPage {
  constructor(view) {
    this.view = view;
    this.countries = [];
    this.selectedIso3s = [];
  }

  async start() {
    const [indicators, regions] = await Promise.all([fetchIndicators(), fetchRegions()]);
    const region = regions.includes(DEFAULT_REGION) ? DEFAULT_REGION : "";
    this.view.renderIndicators(indicators, defaultIndicator(indicators));
    this.view.renderRegions(regions, region);

    this.countries = await fetchCountries(region);
    this.selectedIso3s = defaultSelection(this.countries);
    this.renderCountries();
    this.listen();
    this.view.showStatus("");
  }

  listen() {
    const { view } = this;
    view.regionSelect.addEventListener("change", () => this.changeRegion());
    view.countryList.addEventListener("change", (event) => this.toggleCountry(event.target));
  }

  async changeRegion() {
    this.countries = await fetchCountries(this.view.regionSelect.value);
    // Keep the ticked countries that are in the new region.
    const inRegion = new Set(this.countries.map((country) => country.iso3));
    this.selectedIso3s = this.selectedIso3s.filter((iso3) => inRegion.has(iso3));
    this.renderCountries();
  }

  toggleCountry(checkbox) {
    this.selectedIso3s = checkbox.checked
      ? [...this.selectedIso3s, checkbox.value]
      : this.selectedIso3s.filter((iso3) => iso3 !== checkbox.value);
    this.renderCountries();
  }

  renderCountries() {
    this.view.renderCountries(this.countries, this.selectedIso3s, canSelectMore(this.selectedIso3s));
  }
}

const view = new PeriodAveragesView(document.querySelector("#period-averages"));
new PeriodAveragesPage(view).start().catch((error) => {
  view.showStatus(`Could not load the page: ${error.message}`, { isError: true });
});
