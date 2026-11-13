# Global Health Data Platform

Lab 1 project — "Health spending, immunization and life expectancy across countries, 2000–2023."

A layered Python application that ingests public health data (WHO GHO, World Bank, Our World in Data) into a PostgreSQL database through an ETL pipeline, and shows it in server-side rendered web pages (FastAPI + Jinja2, Lab 3) and through a REST API with a client-side rendered page (Lab 4).

## Tech stack

| Layer | Tooling |
|---|---|
| Data retrieval | `requests`, `pandas` |
| Data cleaning | `pandas`, `pycountry` |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic, psycopg |
| Web (server-side rendering) | FastAPI, Uvicorn, Jinja2 templates |
| REST API | FastAPI, pydantic (OpenAPI docs at `/api/docs`) |
| Client-side rendering | JavaScript ES modules (no build step), Chart.js |
| Testing | pytest, httpx2 |

## Local setup

1. Install Python 3.12+, Git, and PostgreSQL 16+ (this project uses PostgreSQL 18 at `D:\pgsql`).
2. Start the database server:
   ```
   D:\pgsql\bin\pg_ctl.exe -D D:\pgsql\data -l D:\pgsql\postgres.log start
   ```
3. Create the project user and database (once):
   ```
   D:\pgsql\bin\psql.exe -U postgres -h localhost -d postgres -c "CREATE USER gh_user WITH PASSWORD '<choose-a-password>';"
   D:\pgsql\bin\psql.exe -U postgres -h localhost -d postgres -c "CREATE DATABASE global_health OWNER gh_user ENCODING 'UTF8';"
   ```
4. Create the virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
5. Configure the database connection: copy `.env.example` to `.env` and put the
   password you chose in step 3 into `DATABASE_URL`:
   ```
   copy .env.example .env
   ```
6. Create the database schema:
   ```
   alembic upgrade head
   ```

## Architecture

The web app is split into layers; each layer only calls the one below it.
The HTML pages follow the MVT pattern (model, view, template), and the REST
controllers return JSON built from the same services:

| Layer | Package | Responsibility |
|---|---|---|
| Presentation | `app/controllers/`, `app/templates/` | FastAPI routes read the request, call one service, render a Jinja2 template |
| Presentation (REST) | `app/controllers/api/` | FastAPI routes under `/api` read the request, call one service, return JSON (pydantic schemas in `schemas.py`); service errors become HTTP status codes |
| Service | `app/services/` | Business rules: paging, filter choices, per-period averages, running the ETL steps |
| Data access | `app/repositories/` | All SQLAlchemy queries; returns the plain types in `app/domain.py` |
| Model | `app/models.py`, `app/database.py` | ORM tables and database sessions |

`app/dependencies.py` wires the layers together with FastAPI `Depends`. The ETL
pipeline lives in `etl/` (extract, transform, clean, load); `etl/import_runner.py`
holds the Transform & Load loop shared by the per-source import scripts.

## REST API

REST (REpresentational State Transfer) exposes data as **resources**, each
with its own URL, and uses the HTTP **verb** to say what to do with it. The
server keeps no session between requests (each request is stateless), the
body is a representation of the resource (JSON here), and the **status code**
says how it went.

| Verb | Meaning | Example | Safe | Idempotent |
|---|---|---|---|---|
| `GET` | Read a resource or a list | `GET /api/countries` | yes | yes |
| `POST` | Create a resource, or run an action | `POST /api/observations` | no | no |
| `PUT` | Replace a resource completely | `PUT /api/indicators/SH.IMM.MEAS` | no | yes |
| `PATCH` | Change some fields of a resource | `PATCH /api/countries/ROU` | no | no* |
| `DELETE` | Remove a resource | `DELETE /api/observations/42` | no | yes |

*Safe* means the request changes nothing on the server, so it can be cached,
prefetched or retried freely. *Idempotent* means sending it twice has the same
effect as sending it once (\*PATCH can be written to be idempotent, but HTTP
does not require it). Common status codes: `200 OK`, `201 Created`,
`204 No Content`, `400 Bad Request`, `404 Not Found`,
`422 Unprocessable Content` (the request is well formed but its values are
not valid), `500 Internal Server Error`.

This API only reads data, so all its endpoints are `GET`. The ETL buttons
change data, so they are `POST` forms (`/actions/extract`, `/actions/load`).

| Endpoint | Returns |
|---|---|
| `GET /api/regions` | Region names |
| `GET /api/countries?region=Europe %26 Central Asia` | Countries (`iso3`, `name`), all or of one region |
| `GET /api/indicators` | Indicators (`code`, `name`) |
| `GET /api/indicators/{code}/period-averages?country=ROU&country=FRA&first_year=2000&last_year=2023&period_years=5` | The indicator's average per country for each period of `period_years` years (only both-sexes values, rounded to 2 decimals; `null` where a country has no data) |

Example: `GET /api/indicators/OWID_LIFE_EXPECTANCY/period-averages?country=ROU&country=FRA`

```json
{
  "indicator": {"code": "OWID_LIFE_EXPECTANCY", "name": "Life expectancy (OWID)", "unit": "years"},
  "periods": [{"start": 2000, "end": 2004, "label": "2000–2004"}, "…",
              {"start": 2020, "end": 2023, "label": "2020–2023"}],
  "series": [
    {"country_iso3": "FRA", "country_name": "France", "averages": [79.49, 80.85, 81.87, 82.46, 82.58]},
    {"country_iso3": "ROU", "country_name": "Romania", "averages": [71.01, 72.64, 74.37, 75.04, 74.5]}
  ]
}
```

An unknown indicator returns `404`; reversed years, a period under 1 year or
more than 20 countries return `422`. With the app running, the interactive
OpenAPI documentation is at http://127.0.0.1:8000/api/docs.

## Client-side rendering

`/` (Lab 3) is rendered on the server: each filter change reloads the page,
and the HTML arrives complete. `/period-averages` (Lab 4) is rendered in the
browser: the server sends an empty page shell, the JavaScript calls the REST
API, and builds the table and the chart from the JSON. Changing a filter
fetches only new data; the page never reloads.

The page compares an indicator, by default life expectancy, averaged over
5-year periods (2000–2004, …, 2020–2023), for countries picked from a
drop-down (default: Europe & Central Asia, five countries; at most 8, one
color per line). The JavaScript in `app/static/js/` uses the same layers as
the backend:

| Layer | File | Responsibility |
|---|---|---|
| Data access | `api-client.js` | The only module that calls `fetch`; one function per endpoint |
| Business logic | `period-averages-model.js` | Defaults, selection rules, stable colors per country, report → table rows / chart lines |
| Presentation | `period-averages-view.js` | Draws the drop-downs, the table and the Chart.js line chart; no logic |
| Controller | `period-averages-page.js` | Reacts to the filters, cancels outdated requests, connects the layers |

## Running the app

```
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000, click **Extract** to download the raw data, then
**Transform & load** to fill the database. The client-side page is at
http://127.0.0.1:8000/period-averages and the API docs at
http://127.0.0.1:8000/api/docs.

## Running the tests

```
python -m pytest
```

The repository tests and the full-stack controller tests in `tests/` need a
reachable PostgreSQL; the service tests and most REST controller tests use
in-memory fakes and always run. They use
`TEST_DATABASE_URL`, or `DATABASE_URL` if that is not set, but never touch the
application data: each run creates a temporary `test_<random>` schema, rolls
back every test, and drops the schema at the end. Without a database those
tests are skipped. The Extract and Load actions are stubbed, so the tests make
no network calls.
