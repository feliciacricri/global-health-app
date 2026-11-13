"""REST controller for the lookup lists a client needs to build its filters.

Read-only resources, so only GET: safe and idempotent, cacheable.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.controllers.api.schemas import CountryResponse, IndicatorResponse
from app.dependencies import get_observation_service
from app.services.observation_service import ObservationService

router = APIRouter(prefix="/api", tags=["reference data"])

Service = Annotated[ObservationService, Depends(get_observation_service)]


@router.get("/regions")
def list_regions(service: Service) -> list[str]:
    return list(service.list_regions())


@router.get("/countries")
def list_countries(service: Service, region: str | None = None) -> list[CountryResponse]:
    """All countries sorted by name, or only those in ``region``."""
    return [CountryResponse.from_option(c) for c in service.list_countries(region)]


@router.get("/indicators")
def list_indicators(service: Service) -> list[IndicatorResponse]:
    return [IndicatorResponse.from_option(i) for i in service.list_indicators()]
