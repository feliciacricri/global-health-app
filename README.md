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

## Running the tests

```
python -m pytest
```

The Extract and Load actions are stubbed, so the tests make no network calls
and need no database.
