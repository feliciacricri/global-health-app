"""Presentation layer: the ETL buttons, with a fake service (no network, no DB)."""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_etl_service
from app.main import app
from app.services.etl_service import StepResult

RESULTS = [
    StepResult.ok("World Bank", "SH.IMM.MEAS", "raw=10 clean=8 loaded=8"),
    StepResult.failed("WHO GHO", "WHOSIS_000001", "HTTPError: 500 <Server Error>"),
]


class FakeEtlService:
    def __init__(self, results: list[StepResult]) -> None:
        self._results = results
        self.calls: list[str] = []

    def extract_all(self) -> list[StepResult]:
        self.calls.append("extract")
        return self._results

    def transform_and_load_all(self) -> list[StepResult]:
        self.calls.append("transform_and_load")
        return self._results


def _use(service: FakeEtlService) -> None:
    app.dependency_overrides[get_etl_service] = lambda: service


@pytest.mark.parametrize(
    ("url", "expected_call", "heading"),
    [
        ("/actions/extract", "extract", "Extract complete"),
        ("/actions/load", "transform_and_load", "Transform &amp; Load complete"),
    ],
)
def test_action_runs_its_step_once_and_shows_each_result(
    client: TestClient, url: str, expected_call: str, heading: str
) -> None:
    service = FakeEtlService(RESULTS)
    _use(service)

    response = client.post(url)

    assert response.status_code == 200
    assert service.calls == [expected_call]
    html = response.text
    assert f"<h1>{heading}</h1>" in html
    assert "<td>SH.IMM.MEAS</td>" in html
    assert "<td>raw=10 clean=8 loaded=8</td>" in html
    assert "<td>failed</td>" in html
    # result messages come from external errors, so they must be escaped
    assert "HTTPError: 500 &lt;Server Error&gt;" in html
    assert 'href="/"' in html


@pytest.mark.parametrize("url", ["/actions/extract", "/actions/load"])
def test_action_with_no_results(client: TestClient, url: str) -> None:
    _use(FakeEtlService([]))

    assert "No results." in client.post(url).text


@pytest.mark.parametrize("url", ["/actions/extract", "/actions/load"])
def test_actions_reject_get(client: TestClient, url: str) -> None:
    # a GET (link click, crawler, prefetch) must not start a download or load
    assert client.get(url).status_code == 405
