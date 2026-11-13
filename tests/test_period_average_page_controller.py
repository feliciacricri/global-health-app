"""Presentation layer (client-side rendering): the page shell and its scripts.

The page itself needs no database; the ``client`` fixture fails any test
that touches one.
"""

import pytest
from fastapi.testclient import TestClient

SCRIPTS = [
    "api-client.js",
    "period-averages-model.js",
    "period-averages-view.js",
    "period-averages-page.js",
]


def test_page_shell_loads_the_client_side_code(client: TestClient) -> None:
    response = client.get("/period-averages")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert '<script type="module" src="http://testserver/static/js/period-averages-page.js">' in html
    assert 'href="/api/docs"' in html
    # Filled in by the browser, not by the server.
    assert '<select id="indicator"></select>' in html
    assert '<ul id="country-list"></ul>' in html


@pytest.mark.parametrize("script", SCRIPTS)
def test_scripts_are_served_as_javascript(client: TestClient, script: str) -> None:
    response = client.get(f"/static/js/{script}")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_navigation_links_both_pages(client: TestClient) -> None:
    html = client.get("/period-averages").text

    assert '<a href="/">Observations</a>' in html
    assert '<a href="/period-averages">Averages per period</a>' in html
