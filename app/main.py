"""Application entry point: ``uvicorn app.main:app``.

Layers:
- data access: ``app.repositories`` (SQLAlchemy queries)
- service: ``app.services`` (business rules, ETL orchestration)
- presentation: ``app.controllers``
  - server-side rendering (MVT): routes + ``app/templates`` (Jinja2)
  - REST API: ``app.controllers.api`` (JSON under ``/api``)
"""

from fastapi import FastAPI

from app.controllers import etl_controller, observation_controller
from app.controllers.api import reference_data_api

API_DOCS_URL = "/api/docs"


def create_app() -> FastAPI:
    # The OpenAPI schema and its docs page describe only the JSON API; the
    # HTML routes are left out of it.
    app = FastAPI(
        title="Global Health Data Platform",
        openapi_url="/api/openapi.json",
        docs_url=API_DOCS_URL,
        redoc_url=None,
    )
    app.include_router(observation_controller.router)
    app.include_router(etl_controller.router)
    app.include_router(reference_data_api.router)
    return app


app = create_app()
