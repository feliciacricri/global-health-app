"""Controller for the client-side rendered averages page.

It only serves the page shell; the browser fills it in from the REST API
(``app.controllers.api``), so this route needs no service and no database.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.controllers.api import API_DOCS_URL
from app.controllers.templating import templates
from app.services.period_average_service import (
    DEFAULT_FIRST_YEAR,
    DEFAULT_LAST_YEAR,
)

router = APIRouter(include_in_schema=False)

# The chart has 8 distinct line colors (see period-averages-model.js).
MAX_CHART_COUNTRIES = 8


@router.get("/period-averages", response_class=HTMLResponse)
def show_period_averages(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "period_averages.html",
        {
            "first_year": DEFAULT_FIRST_YEAR,
            "last_year": DEFAULT_LAST_YEAR,
            "max_countries": MAX_CHART_COUNTRIES,
            "api_docs_url": API_DOCS_URL,
        },
    )
