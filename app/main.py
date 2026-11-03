import math
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.actions import extract_all, load_all
from app.database import get_db
from app.models import Country, Indicator, Observation

app = FastAPI(title="Global Health Data Platform")

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=_TEMPLATE_DIR)

PAGE_SIZE = 50

# country/year alone has ties (several indicators and sexes per country-year);
# with LIMIT/OFFSET, Postgres may order ties differently per query, so rows
# could repeat or vanish between pages. The trailing PK makes it total.
_ORDER_BY = (
    Country.name,
    Observation.year.desc(),
    Indicator.code,
    Observation.sex,
    Observation.observation_id,
)


def _to_int(value: str | None) -> int | None:
    # Not str.isdigit(): it accepts e.g. "²", which int() then rejects (500).
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _build_query(
    country: str | None,
    indicator: str | None,
    region: str | None,
    year_from: int | None,
    year_to: int | None,
):
    stmt = (
        select(
            Country.name.label("country"),
            Country.iso3,
            Country.region,
            Indicator.code.label("indicator_code"),
            Indicator.name.label("indicator"),
            Indicator.unit,
            Observation.year,
            Observation.sex,
            Observation.value,
        )
        .join(Country, Observation.country_iso3 == Country.iso3)
        .join(Indicator, Observation.indicator_id == Indicator.indicator_id)
    )
    if country:
        stmt = stmt.where(Country.iso3 == country)
    if indicator:
        stmt = stmt.where(Indicator.code == indicator)
    if region:
        stmt = stmt.where(Country.region == region)
    if year_from:
        stmt = stmt.where(Observation.year >= year_from)
    if year_to:
        stmt = stmt.where(Observation.year <= year_to)

    return stmt


@app.get("/api/observations")
def list_observations(
    country: str | None = None,
    indicator: str | None = None,
    region: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = (
        _build_query(country, indicator, region, year_from, year_to)
        .order_by(*_ORDER_BY)
        .limit(limit)
        .offset(offset)
    )

    return [dict(row) for row in db.execute(stmt).mappings()]


@app.get("/", response_class=HTMLResponse)
def observations_page(
    request: Request,
    country: str | None = None,
    indicator: str | None = None,
    region: str | None = None,
    year_from: str | None = None,
    year_to: str | None = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    year_from_int = _to_int(year_from)
    year_to_int = _to_int(year_to)
    base = _build_query(country, indicator, region, year_from_int, year_to_int)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    rows = (
        db.execute(
            base.order_by(*_ORDER_BY)
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        )
        .mappings()
        .all()
    )

    countries = db.execute(
        select(Country.iso3, Country.name).order_by(Country.name)
    ).all()
    indicators = db.execute(
        select(Indicator.code, Indicator.name).order_by(Indicator.name)
    ).all()
    regions = (
        db.execute(select(Country.region).distinct().order_by(Country.region))
        .scalars()
        .all()
    )
    pages = max(1, math.ceil(total / PAGE_SIZE))

    return templates.TemplateResponse(
        request,
        "observations.html",
        {
            "rows": rows,
            "total": total,
            "page": page,
            "pages": pages,
            "countries": countries,
            "indicators": indicators,
            "regions": regions,
            "filters": {
                "country": country,
                "indicator": indicator,
                "region": region,
                "year_from": year_from_int,
                "year_to": year_to_int,
            },
            "prev_url": (
                request.url.include_query_params(page=page - 1) if page > 1 else None
            ),
            "next_url": (
                request.url.include_query_params(page=page + 1)
                if page < pages
                else None
            ),
        },
    )


@app.post("/actions/extract", response_class=HTMLResponse)
def run_extract(request: Request):
    results = extract_all()

    return templates.TemplateResponse(
        request,
        "action_result.html",
        {
            "action": "Extract",
            "description": "Downloaded fresh data from WHO, World Bank and Our World in Data into data/raw/.",
            "results": results,
        },
    )


@app.post("/actions/load", response_class=HTMLResponse)
def run_load(request: Request):
    results = load_all()

    return templates.TemplateResponse(
        request,
        "action_result.html",
        {
            "action": "Transform & Load",
            "description": "Transformed the cached raw files to a common format, cleaned them, and upserted them into the database.",
            "results": results,
        },
    )
