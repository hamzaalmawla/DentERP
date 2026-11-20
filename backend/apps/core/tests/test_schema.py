"""OpenAPI schema at /api/v1/schema/ and Swagger UI at /api/v1/docs/ (SYS-09)."""

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_schema_builds_and_validates(tmp_path):
    out = tmp_path / "schema.yml"

    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(out))

    assert "SPU Dental Clinic System API" in out.read_text()


def test_schema_endpoint_is_public():
    response = APIClient().get("/api/v1/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "SPU Dental Clinic System API"


def test_docs_page():
    response = APIClient().get("/api/v1/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()


@pytest.mark.urls("tests.testapp.urls")
def test_schema_covers_module_endpoints():
    schema = APIClient().get("/api/v1/schema/?format=json").json()

    assert "/api/v1/test/notes/" in schema["paths"]
    parameters = {p["name"] for p in schema["paths"]["/api/v1/test/notes/"]["get"]["parameters"]}
    assert {"page", "page_size", "ordering", "title"} <= parameters
