// Presentation layer (client): draws the filters, the table and the chart.
// It only renders what it is given; it never fetches or decides anything.
// Text is set with textContent, never innerHTML, so API data cannot inject markup.

const MISSING = "—";
const SERIES_COLOR_COUNT = 8;
const numberFormat = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export class PeriodAveragesView {
  constructor(root) {
    this.indicatorSelect = root.querySelector("#indicator");
    this.regionSelect = root.querySelector("#region");
    this.periodSelect = root.querySelector("#period-years");
    this.countrySummary = root.querySelector("#country-summary");
    this.countryList = root.querySelector("#country-list");
    this.status = root.querySelector("#status");
    this.table = root.querySelector("#averages-table");
    this.canvas = root.querySelector("#averages-chart");
    this.chart = null;
  }

  get seriesColorCount() {
    return SERIES_COLOR_COUNT;
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

  renderPeriodChoices(choices, selectedYears) {
    replaceOptions(
      this.periodSelect,
      choices.map((years) => [String(years), years === 1 ? "1 year" : `${years} years`]),
      String(selectedYears),
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

  clearResults() {
    this.table.replaceChildren();
    this.chart?.destroy();
    this.chart = null;
  }

  renderTable({ columns, rows }) {
    const headerRow = document.createElement("tr");
    const periodHeaders = columns.map((column) => {
      const cell = headerCell(column, "col");
      cell.className = "number";
      return cell;
    });
    headerRow.append(headerCell("Country", "col"), ...periodHeaders);
    const head = document.createElement("thead");
    head.append(headerRow);

    const body = document.createElement("tbody");
    for (const row of rows) {
      const tableRow = document.createElement("tr");
      tableRow.append(headerCell(row.label, "row"));
      for (const value of row.cells) {
        const cell = document.createElement("td");
        cell.className = "number";
        cell.textContent = value === null ? MISSING : numberFormat.format(value);
        tableRow.append(cell);
      }
      body.append(tableRow);
    }
    this.table.replaceChildren(head, body);
  }

  renderChart({ labels, yTitle, lines }) {
    const style = getComputedStyle(this.canvas);
    const token = (name) => style.getPropertyValue(name).trim();
    const datasets = lines.map((line) => {
      const color = token(`--series-${line.colorSlot + 1}`);
      return {
        label: line.label,
        data: line.values,
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBorderColor: token("--chart-surface"),
        pointBorderWidth: 2,
        // A period without data is a gap in the line, not an invented value.
        spanGaps: false,
      };
    });

    this.chart?.destroy();
    this.chart = new window.Chart(this.canvas, {
      type: "line",
      data: { labels, datasets },
      options: chartOptions(yTitle, token),
    });
  }
}

function chartOptions(yTitle, token) {
  const ink = token("--chart-text");
  const grid = token("--chart-grid");
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    // Hovering anywhere over a period shows every country's value there.
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom", labels: { color: ink, usePointStyle: true } },
      tooltip: {
        callbacks: {
          label: (item) =>
            `${item.dataset.label}: ${
              item.parsed.y === null ? MISSING : numberFormat.format(item.parsed.y)
            }`,
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: "Period", color: ink },
        ticks: { color: ink },
        grid: { display: false },
      },
      y: {
        title: { display: true, text: yTitle, color: ink },
        ticks: { color: ink },
        grid: { color: grid },
        border: { display: false },
      },
    },
  };
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

function headerCell(text, scope) {
  const cell = document.createElement("th");
  cell.scope = scope;
  cell.textContent = text;
  return cell;
}
