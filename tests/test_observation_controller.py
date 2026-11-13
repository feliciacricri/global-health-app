"""Presentation layer: GET / renders the observations page (full stack + DB)."""

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_observation_service
from app.main import app
from app.repositories.observation_repository import ObservationRepository
from app.services.observation_service import ObservationService

pytestmark = pytest.mark.usefixtures("seeded")


@pytest.fixture
def client(client_with_db: TestClient) -> TestClient:
    return client_with_db


@pytest.fixture
def small_pages(client: TestClient) -> Iterator[None]:
    """Pages of 4 rows, so the 9 seeded rows span 3 pages."""

    def service(session: Annotated[Session, Depends(get_db)]) -> ObservationService:
        return ObservationService(ObservationRepository(session), page_size=4)

    app.dependency_overrides[get_observation_service] = service
    yield


def test_page_lists_rows_and_filter_options(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "9 rows · page 1 of 1" in html
    assert "<td>Romania (ROU)</td>" in html
    assert '<option value="ROU" >Romania</option>' in html
    assert '<option value="WHOSIS_000001" >Life expectancy at birth</option>' in html
    assert '<option value="Europe &amp; Central Asia" >' in html


def test_filters_narrow_rows_and_stay_selected(client: TestClient) -> None:
    html = client.get(
        "/", params={"country": "ROU", "indicator": "WHOSIS_000001", "year_from": "2015"}
    ).text

    assert "3 rows · page 1 of 1" in html
    assert '<option value="ROU" selected>Romania</option>' in html
    assert '<option value="WHOSIS_000001" selected>' in html
    assert 'name="year_from" placeholder="From year" value="2015"' in html
    assert "Kenya (KEN)" not in html


def test_blank_form_fields_mean_no_filter(client: TestClient) -> None:
    params = {"country": "", "indicator": "", "region": "", "year_from": "", "year_to": ""}

    assert "9 rows · page 1 of 1" in client.get("/", params=params).text


@pytest.mark.parametrize("bad_year", ["abc", "²", "2020.5"])
def test_unparseable_years_are_ignored_not_errors(
    client: TestClient, bad_year: str
) -> None:
    response = client.get("/", params={"year_from": bad_year, "year_to": bad_year})

    assert response.status_code == 200
    assert "9 rows · page 1 of 1" in response.text


def test_no_matches_shows_empty_message(client: TestClient) -> None:
    html = client.get("/", params={"country": "XXX"}).text

    assert "0 rows · page 1 of 1" in html
    assert "No data matches these filters." in html


def test_values_are_formatted_and_missing_values_show_a_dash(client: TestClient) -> None:
    html = client.get("/", params={"country": "KEN"}).text

    assert "<td>61.40</td>" in html
    assert "<td>-</td>" in html


@pytest.mark.usefixtures("small_pages")
@pytest.mark.parametrize(
    ("page", "has_previous", "has_next"),
    [(1, False, True), (2, True, True), (3, True, False)],
)
def test_pagination_links(
    client: TestClient, page: int, has_previous: bool, has_next: bool
) -> None:
    html = client.get("/", params={"page": page}).text

    assert f"9 rows · page {page} of 3" in html
    assert (">Previous</a>" in html) == has_previous
    assert (">Next</a>" in html) == has_next
    if has_previous:
        assert f'href="http://testserver/?page={page - 1}"' in html
    if has_next:
        assert f'href="http://testserver/?page={page + 1}"' in html


@pytest.mark.usefixtures("small_pages")
def test_pagination_keeps_the_filters(client: TestClient) -> None:
    html = client.get("/", params={"region": "Europe & Central Asia"}).text

    assert "7 rows · page 1 of 2" in html
    assert "?region=Europe+%26+Central+Asia&amp;page=2" in html


def test_page_must_be_positive(client: TestClient) -> None:
    assert client.get("/", params={"page": 0}).status_code == 422
