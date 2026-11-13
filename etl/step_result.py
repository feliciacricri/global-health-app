"""Typed results of the ETL steps, shared by the import scripts and the web app."""

from dataclasses import dataclass
from enum import StrEnum


class StepStatus(StrEnum):
    OK = "ok"
    SKIPPED = "skip"
    FAILED = "failed"


@dataclass(frozen=True)
class StepResult:
    """Outcome of extracting or importing one item from one source."""

    source: str
    item: str
    status: StepStatus
    message: str

    @classmethod
    def ok(cls, source: str, item: str, message: str) -> "StepResult":
        return cls(source, item, StepStatus.OK, message)

    @classmethod
    def skipped(cls, source: str, item: str, message: str) -> "StepResult":
        return cls(source, item, StepStatus.SKIPPED, message)

    @classmethod
    def failed(cls, source: str, item: str, message: str) -> "StepResult":
        return cls(source, item, StepStatus.FAILED, message)

    @classmethod
    def from_error(cls, source: str, item: str, error: Exception) -> "StepResult":
        return cls.failed(source, item, f"{type(error).__name__}: {error}")
