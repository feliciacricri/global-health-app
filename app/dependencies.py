"""Wires the layers together for FastAPI; tests swap these via dependency_overrides."""

from app.services.etl_service import EtlService


def get_etl_service() -> EtlService:
    return EtlService()
