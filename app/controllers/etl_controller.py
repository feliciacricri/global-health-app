"""Controller for the ETL buttons: runs a step, renders its results as HTML."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.controllers.templating import templates
from app.dependencies import get_etl_service
from app.services.etl_service import EtlService, StepResult

# POST only: a GET (link click, crawler, prefetch) must not start a download.
router = APIRouter(prefix="/actions", include_in_schema=False)


@router.post("/extract", response_class=HTMLResponse)
def extract(
    request: Request, service: Annotated[EtlService, Depends(get_etl_service)]
) -> HTMLResponse:
    return _render_step_results(
        request,
        action="Extract",
        description=(
            "Downloaded fresh data from WHO, World Bank and Our World in Data "
            "into data/raw/."
        ),
        results=service.extract_all(),
    )


@router.post("/load", response_class=HTMLResponse)
def transform_and_load(
    request: Request, service: Annotated[EtlService, Depends(get_etl_service)]
) -> HTMLResponse:
    return _render_step_results(
        request,
        action="Transform & Load",
        description=(
            "Transformed the cached raw files to a common format, cleaned them, "
            "and upserted them into the database."
        ),
        results=service.transform_and_load_all(),
    )


def _render_step_results(
    request: Request, *, action: str, description: str, results: list[StepResult]
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "action_result.html",
        {"action": action, "description": description, "results": results},
    )
