"""Lists: page and page_size, 20 by default and 100 at most; filters and ordering."""

import pytest

from tests.testapp.models import Note

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.testapp.urls")]

URL = "/api/v1/test/notes/"


@pytest.fixture
def notes():
    Note.objects.bulk_create(Note(title=f"note {i:03}") for i in range(130))


def test_default_page_size_is_20(api, notes):
    body = api.get(URL).json()

    assert body["count"] == 130
    assert len(body["results"]) == 20
    assert body["next"].endswith("?page=2")
    assert body["previous"] is None


def test_page_size_parameter(api, notes):
    body = api.get(URL, {"page_size": 5, "page": 2}).json()

    assert [note["title"] for note in body["results"]] == [f"note {i:03}" for i in range(5, 10)]


def test_page_size_maximum_is_100(api, notes):
    body = api.get(URL, {"page_size": 500}).json()

    assert len(body["results"]) == 100


def test_page_out_of_range_uses_the_error_format(api, notes):
    response = api.get(URL, {"page": 99}, HTTP_ACCEPT_LANGUAGE="en")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert set(response.json()) == {"code", "message", "details"}


def test_filter_and_ordering_defaults(api, notes):
    filtered = api.get(URL, {"title": "note 007"}).json()
    ordered = api.get(URL, {"ordering": "-title", "page_size": 1}).json()

    assert [note["title"] for note in filtered["results"]] == ["note 007"]
    assert ordered["results"][0]["title"] == "note 129"


def test_inactive_rows_are_not_listed(api, notes):
    Note.objects.filter(title="note 000").deactivate()

    assert api.get(URL).json()["count"] == 129


def test_dates_are_utc(api):
    Note.objects.create(title="a")

    created_at = api.get(URL).json()["results"][0]["created_at"]

    assert created_at.endswith("Z")
