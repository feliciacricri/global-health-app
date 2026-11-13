"""Application entry point: ``uvicorn app.main:app``.

Layers:
- data access: ``app.repositories`` (SQLAlchemy queries)
- service: ``app.services`` (business rules, ETL orchestration)
- presentation: ``app.controllers``
  - server-side rendering (MVT): routes + ``app/templates`` (Jinja2)
  - REST API: ``app.controllers.api`` (JSON under ``/api``)
  - client-side rendering: a page shell + ``app/static/js`` that calls the API
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.controllers import (
    etl_controller,
    observation_controller,
    period_average_page_controller,
)
from app.controllers.api import API_DOCS_URL, period_average_api, reference_data_api

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    # The OpenAPI schema and its docs page describe only the JSON API; the
    # HTML routes are left out of it.
    app = FastAPI(
        title="Global Health Data Platform",
        openapi_url="/api/openapi.json",
        docs_url=API_DOCS_URL,
        redoc_url=None,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(observation_controller.router)
    app.include_router(period_average_page_controller.router)
    app.include_router(etl_controller.router)
    app.include_router(reference_data_api.router)
    app.include_router(period_average_api.router)
    return app


app = create_app()
