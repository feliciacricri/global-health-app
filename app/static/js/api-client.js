// Data access layer (client): the only module that talks to the REST API.
// Each function issues one GET and resolves to the parsed JSON body.

const API_ROOT = "/api";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
  }
}

async function getJson(path, params = new URLSearchParams(), signal = undefined) {
  const query = params.toString();
  const url = query ? `${API_ROOT}${path}?${query}` : `${API_ROOT}${path}`;
  const response = await fetch(url, { headers: { Accept: "application/json" }, signal });
  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response));
  }
  return response.json();
}

async function errorDetail(response) {
  try {
    const body = await response.json();
    // FastAPI sends {"detail": "..."} for our errors and a list for 422
    // validation errors.
    return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    return response.statusText;
  }
}

export function fetchRegions() {
  return getJson("/regions");
}

export function fetchCountries(region) {
  const params = new URLSearchParams();
  if (region) {
    params.set("region", region);
  }
  return getJson("/countries", params);
}

export function fetchIndicators() {
  return getJson("/indicators");
}

/**
 * @param {{indicatorCode: string, countryIso3s: string[], firstYear: number,
 *          lastYear: number, periodYears: number}} query
 * @param {AbortSignal} signal lets the caller cancel a request it no longer needs.
 */
export function fetchPeriodAverages(query, signal) {
  const params = new URLSearchParams({
    first_year: String(query.firstYear),
    last_year: String(query.lastYear),
    period_years: String(query.periodYears),
  });
  for (const iso3 of query.countryIso3s) {
    params.append("country", iso3);
  }
  const code = encodeURIComponent(query.indicatorCode);
  return getJson(`/indicators/${code}/period-averages`, params, signal);
}
