"""The OpenAPI outline of the Release 1 endpoints (P0.5, design section 7).

Every planned endpoint is in the schema, refuses the roles that will not be allowed (403) and
anonymous callers (401), and answers the allowed roles with 501 ``not_implemented``. When a
module builds an endpoint, its placeholder disappears from this test on its own.
"""

import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from apps.accounts.domain.roles import RoleCode
from apps.accounts.models import Role, User, UserRole
from apps.accounts.testing.api import bearer, login

pytestmark = pytest.mark.django_db

PASSWORD = "Strong-Pass-2026"


def _walk(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern):
            yield prefix + str(pattern.pattern), pattern.callback


def planned_operations():
    """(path, method, Planned) for every placeholder endpoint."""
    for route, callback in _walk(get_resolver().url_patterns):
        view = getattr(callback, "view_class", None)
        for method, planned in getattr(view, "planned_operations", {}).items():
            path = "/" + re.sub(r"<int:\w+>", "1", route)
            yield path, method, planned


PLANNED = sorted(planned_operations(), key=lambda op: (op[0], op[1]))


def _schema_path(path: str) -> str:
    return re.sub(r"/1/", "/{id}/", path)


def _call(client, method, path):
    return getattr(client, method)(path, {}, format="json")


@pytest.fixture
def token_for():
    def make(role: str) -> str:
        user = User.objects.create_user(f"user_{role}", PASSWORD, full_name_ar="مستخدم")
        UserRole.objects.create(user=user, role=Role.objects.get(code=role))
        response = login(user.username, PASSWORD)
        assert response.status_code == 200, response.json()
        return response.json()["access"]

    return make


def test_every_release1_endpoint_is_planned():
    planned = {(_schema_path(path), method) for path, method, _ in PLANNED}

    assert len(planned) == len(PLANNED)
    # Built endpoints leave this list; their module's tests take over (P1.1: /lookups/,
    # /clinics/).
    assert {
        ("/api/v1/patients/", "get"),
        ("/api/v1/diagnosis-queue/{id}/assign/", "post"),
        ("/api/v1/diagnoses/{id}/", "patch"),
        ("/api/v1/referrals/{id}/eligible-students/", "get"),
        ("/api/v1/steps/{id}/approve/", "post"),
        ("/api/v1/approvals/", "get"),
        ("/api/v1/media/", "post"),
        ("/api/v1/clinics/{id}/today/", "get"),
        ("/api/v1/attendance/", "post"),
        ("/api/v1/rounds/", "post"),
        ("/api/v1/tickets/{id}/resolve/", "post"),
        ("/api/v1/chairs/{id}/status/", "post"),
        ("/api/v1/notifications/read/", "post"),
    } <= planned


def test_deferred_endpoints_are_not_planned():
    planned = {(_schema_path(path), method) for path, method, _ in PLANNED}

    assert ("/api/v1/cases/", "post") not in planned  # lab cases (ST-10)
    assert not {path for path, _ in planned} & {"/api/v1/logbook/", "/api/v1/case-finder/"}


def test_the_schema_has_every_planned_operation():
    schema = APIClient().get("/api/v1/schema/?format=json").json()

    for path, method, _ in PLANNED:
        operation = schema["paths"][_schema_path(path)][method]
        assert "501" in operation["responses"], (path, method)


@pytest.mark.parametrize(
    ("path", "method", "role"),
    [
        (path, method, role)
        for path, method, p in PLANNED
        for role in sorted(p.permission.allowed_roles)
    ],
)
def test_allowed_roles_get_not_implemented(token_for, path, method, role):
    response = _call(bearer(token_for(role)), method, path)

    assert response.status_code == 501
    assert response.json()["code"] == "not_implemented"
    assert response.json()["details"]["planned_in"].startswith("P1.")


@pytest.mark.parametrize(
    ("path", "method", "role"),
    [
        (path, method, next(r for r in RoleCode if r not in p.permission.allowed_roles))
        for path, method, p in PLANNED
        if set(RoleCode) - p.permission.allowed_roles
    ],
)
def test_another_role_is_refused(token_for, path, method, role):
    response = _call(bearer(token_for(role)), method, path)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


@pytest.mark.parametrize(("path", "method"), [(path, method) for path, method, _ in PLANNED])
def test_anonymous_callers_are_refused(path, method):
    response = _call(APIClient(), method, path)

    assert response.status_code == 401


def test_the_message_is_in_arabic(token_for):
    client = bearer(token_for("supervisor"), language="ar")

    response = client.get("/api/v1/approvals/")

    assert response.json()["message"] == "هذه الواجهة مخطط لها ولم تُبنَ بعد."
