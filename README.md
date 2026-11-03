# Global Health Data Platform

Lab 1 project — "Health spending, immunization and life expectancy across countries, 2000–2023."

A layered Python application that ingests public health data (WHO GHO, World Bank, Our World in Data) into a PostgreSQL database, exposes it through a FastAPI REST API, and renders it in a simple web UI.

## Tech stack

| Layer | Tooling |
|---|---|
| Data retrieval | `requests`, `pandas` |
| Data cleaning | `pandas`, `pycountry` |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic, psycopg |
| Backend REST API | FastAPI, Uvicorn, Pydantic |
| UI | Jinja2 templates |
| Testing | pytest, httpx |

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
