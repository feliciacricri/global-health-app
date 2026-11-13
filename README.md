# Global Health Data Platform

Lab 1 project — "Health spending, immunization and life expectancy across countries, 2000–2023."

A layered Python application that ingests public health data (WHO GHO, World Bank, Our World in Data) into a PostgreSQL database through an ETL pipeline, and shows it in server-side rendered web pages (FastAPI + Jinja2). A REST API and client-side rendering are planned for a later lab.

## Tech stack

| Layer | Tooling |
|---|---|
| Data retrieval | `requests`, `pandas` |
| Data cleaning | `pandas`, `pycountry` |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic, psycopg |
| Web (server-side rendering) | FastAPI, Uvicorn, Jinja2 templates |
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

The web app follows the MVT pattern (model, view, template) and is split into
layers; each layer only calls the one below it:

| Layer | Package | Responsibility |
|---|---|---|
| Presentation | `app/controllers/`, `app/templates/` | FastAPI routes read the request, call one service, render a Jinja2 template |
| Service | `app/services/` | Business rules: paging, filter choices, running the ETL steps |
| Data access | `app/repositories/` | All SQLAlchemy queries; returns the plain types in `app/domain.py` |
| Model | `app/models.py`, `app/database.py` | ORM tables and database sessions |

`app/dependencies.py` wires the layers together with FastAPI `Depends`. The ETL
pipeline lives in `etl/` (extract, transform, clean, load); `etl/import_runner.py`
holds the Transform & Load loop shared by the per-source import scripts.

## Running the app

```
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000, click **Extract** to download the raw data, then
**Transform & load** to fill the database.

## Running the tests

```
python -m pytest
```

The API controller tests in `tests/` need a reachable PostgreSQL. They use
`TEST_DATABASE_URL`, or `DATABASE_URL` if that is not set, but never touch the
application data: each run creates a temporary `test_<random>` schema, rolls
back every test, and drops the schema at the end. Without a database those
tests are skipped. The Extract and Load actions are stubbed, so the tests make
no network calls.
