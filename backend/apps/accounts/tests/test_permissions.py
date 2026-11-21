"""Role checks (design section 8, layer 1): X-Active-Role and the permission classes."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.api.permissions import HasAnyRole
from apps.accounts.testing.api import bearer

pytestmark = [pytest.mark.django_db, pytest.mark.urls("apps.accounts.tests.urls")]

ROLES = ["super_admin", "management", "reception", "supervisor", "student", "technician"]


@pytest.mark.parametrize("role", ROLES)
def test_each_permission_class_lets_its_role_in(logged_in, role):
    user, tokens = logged_in(role)

    response = bearer(tokens["access"]).get(f"/api/v1/test/{role}/")

    assert response.status_code == 200
    assert response.json() == {"user_id": user.pk, "role": role}


@pytest.mark.parametrize("role", ROLES)
def test_each_permission_class_refuses_the_other_roles(logged_in, role):
    other = "student" if role != "student" else "technician"
    _, tokens = logged_in(other)

    response = bearer(tokens["access"]).get(f"/api/v1/test/{role}/")

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


@pytest.mark.parametrize("role", ROLES)
def test_each_permission_class_needs_a_login(role):
    response = APIClient().get(f"/api/v1/test/{role}/")

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


class TestHasAnyRole:
    @pytest.mark.parametrize("role", ["student", "supervisor"])
    def test_any_of_the_roles(self, logged_in, role):
        _, tokens = logged_in(role)

        assert bearer(tokens["access"]).get("/api/v1/test/clinical/").status_code == 200

    def test_another_role_is_refused(self, logged_in):
        _, tokens = logged_in("technician")

        assert bearer(tokens["access"]).get("/api/v1/test/clinical/").status_code == 403

    def test_unknown_roles_are_a_programming_error(self):
        with pytest.raises(ValueError, match="dean"):
            HasAnyRole("student", "dean")
        with pytest.raises(ValueError, match="none given"):
            HasAnyRole()


class TestActiveRole:
    def test_a_role_not_held(self, logged_in):
        _, tokens = logged_in("student")

        response = bearer(tokens["access"], role="supervisor").get("/api/v1/test/student/")

        assert response.status_code == 403
        assert response.json() == {
            "code": "role_not_held",
            "message": "You do not hold the role you selected.",
            "details": {"role": "supervisor"},
        }

    def test_a_role_not_held_is_refused_on_every_endpoint(self, logged_in):
        _, tokens = logged_in("student")

        response = bearer(tokens["access"], role="super_admin").get("/api/v1/me/")

        assert response.json()["code"] == "role_not_held"

    def test_the_chosen_role_decides_what_the_user_may_open(self, logged_in):
        _, tokens = logged_in("student", "supervisor")
        as_supervisor = bearer(tokens["access"], role="supervisor")

        assert as_supervisor.get("/api/v1/test/supervisor/").json()["role"] == "supervisor"
        assert as_supervisor.get("/api/v1/test/student/").status_code == 403
        assert as_supervisor.get("/api/v1/test/clinical/").json()["role"] == "supervisor"

    def test_several_roles_without_a_choice(self, logged_in):
        _, tokens = logged_in("student", "supervisor")

        response = bearer(tokens["access"]).get("/api/v1/test/student/")

        assert response.status_code == 403
        assert response.json()["code"] == "active_role_required"

    def test_a_removed_role_is_no_longer_held(self, logged_in):
        user, tokens = logged_in("student", "supervisor")
        user.user_roles.get(role__code="supervisor").deactivate()

        response = bearer(tokens["access"], role="supervisor").get("/api/v1/test/supervisor/")

        assert response.json()["code"] == "role_not_held"

    def test_the_message_is_translated(self, logged_in):
        _, tokens = logged_in("student")

        response = bearer(tokens["access"], role="technician", language="ar").get(
            "/api/v1/test/student/"
        )

        assert response.json()["message"] == "أنت لا تملك الدور الذي اخترته."
