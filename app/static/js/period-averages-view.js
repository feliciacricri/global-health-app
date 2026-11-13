// Presentation layer (client): draws the filters.
// It only renders what it is given; it never fetches or decides anything.
// Text is set with textContent, never innerHTML, so API data cannot inject markup.

export class PeriodAveragesView {
  constructor(root) {
    this.indicatorSelect = root.querySelector("#indicator");
    this.regionSelect = root.querySelector("#region");
    this.countrySummary = root.querySelector("#country-summary");
    this.countryList = root.querySelector("#country-list");
    this.status = root.querySelector("#status");
  }

  renderIndicators(indicators, selectedCode) {
    replaceOptions(
      this.indicatorSelect,
      indicators.map((indicator) => [indicator.code, indicator.name]),
      selectedCode,
    );
  }

  renderRegions(regions, selectedRegion) {
    replaceOptions(
      this.regionSelect,
      [["", "All regions"], ...regions.map((region) => [region, region])],
      selectedRegion,
    );
  }

  /** Checkboxes for ``countries``; unticked ones are disabled when ``canSelectMore`` is false. */
  renderCountries(countries, selectedIso3s, canSelectMore) {
    const selected = new Set(selectedIso3s);
    this.countryList.replaceChildren(
      ...countries.map((country) => {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = country.iso3;
        checkbox.checked = selected.has(country.iso3);
        checkbox.disabled = !checkbox.checked && !canSelectMore;

        const label = document.createElement("label");
        label.append(checkbox, ` ${country.name}`);
        const item = document.createElement("li");
        item.append(label);
        return item;
      }),
    );
    this.countrySummary.textContent = countrySummary(selected.size);
  }

  showStatus(message, { isError = false } = {}) {
    this.status.textContent = message;
    this.status.classList.toggle("error", isError);
  }
}

function countrySummary(count) {
  if (count === 0) {
    return "Choose countries";
  }
  return count === 1 ? "1 country selected" : `${count} countries selected`;
}

function replaceOptions(select, valueLabelPairs, selectedValue) {
  select.replaceChildren(
    ...valueLabelPairs.map(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = value === selectedValue;
      return option;
    }),
  );
}
