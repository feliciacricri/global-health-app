"""POST /actions/extract and /actions/load: run the ETL step, render results.

The real ETL is replaced with stubs (see the autouse guard in conftest), so
these tests never touch the network or the database.
"""

import pytest
from fastapi.testclient import TestClient

import app.main

RESULTS = [
    {"source": "World Bank", "item": "SH.IMM.MEAS", "status": "ok",
     "message": "raw=10 clean=8 loaded=8"},
    {"source": "WHO GHO", "item": "WHOSIS_000001", "status": "failed",
     "message": "HTTPError: 500 <Server Error>"},
]


@pytest.mark.parametrize(
    ("url", "etl_function", "heading"),
    [
        ("/actions/extract", "extract_all", "Extract complete"),
        ("/actions/load", "load_all", "Transform &amp; Load complete"),
    ],
)
def test_action_runs_its_etl_step_once_and_shows_each_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    etl_function: str,
    heading: str,
) -> None:
    calls = []
    monkeypatch.setattr(app.main, etl_function, lambda: calls.append(1) or RESULTS)

    response = client.post(url)

    assert response.status_code == 200
    assert calls == [1]
    html = response.text
    assert f"<h1>{heading}</h1>" in html
    assert "<td>SH.IMM.MEAS</td>" in html
    assert "<td>raw=10 clean=8 loaded=8</td>" in html
    assert "<td>failed</td>" in html
    # result messages come from external errors, so they must be escaped
    assert "HTTPError: 500 &lt;Server Error&gt;" in html
    assert 'href="/"' in html


@pytest.mark.parametrize(
    ("url", "etl_function"),
    [("/actions/extract", "extract_all"), ("/actions/load", "load_all")],
)
def test_action_with_no_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, url: str, etl_function: str
) -> None:
    monkeypatch.setattr(app.main, etl_function, lambda: [])

    assert "No results." in client.post(url).text


@pytest.mark.parametrize("url", ["/actions/extract", "/actions/load"])
def test_actions_reject_get(client: TestClient, url: str) -> None:
    # a GET (link click, crawler, prefetch) must not start a download or load
    assert client.get(url).status_code == 405
