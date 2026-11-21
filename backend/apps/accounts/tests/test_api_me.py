"""GET /me/, POST /me/password/, POST /me/devices/ and the first-login gate."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import DeviceToken
from apps.accounts.testing.api import bearer, login
from apps.core.models import AuditLog

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

ALL_ROLES = ["super_admin", "management", "reception", "supervisor", "student", "technician"]


class TestMe:
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_profile_for_each_role(self, logged_in, role):
        user, tokens = logged_in(
            role, full_name_ar="سارة علي", full_name_en="Sara Ali", university_id="U-1"
        )

        response = bearer(tokens["access"]).get("/api/v1/me/")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == user.pk
        assert (body["full_name_ar"], body["full_name_en"]) == ("سارة علي", "Sara Ali")
        assert body["university_id"] == "U-1"
        assert body["roles"] == [role]
        assert body["active_role"] == role
        assert body["must_change_password"] is False
        assert body["last_login"].endswith("Z")

    def test_not_logged_in(self):
        response = APIClient().get("/api/v1/me/", HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 401
        assert response.json()["code"] == "not_authenticated"

    def test_an_invalid_access_token(self):
        response = bearer("garbage").get("/api/v1/me/")

        assert response.status_code == 401
        assert response.json()["code"] == "token_not_valid"

    def test_a_deactivated_user_is_logged_out(self, logged_in):
        user, tokens = logged_in("student")
        user.deactivate()

        assert bearer(tokens["access"]).get("/api/v1/me/").status_code == 401


class TestFirstLoginGate:
    def test_us04_first_login_must_change_the_temporary_password(self, logged_in):
        _, tokens = logged_in("student", must_change_password=True)
        assert tokens["must_change_password"] is True
        client = bearer(tokens["access"])

        blocked = client.post("/api/v1/me/devices/", {"platform": "android", "token": "t"})
        allowed = client.get("/api/v1/me/")

        assert blocked.status_code == 403
        assert blocked.json() == {
            "code": "password_change_required",
            "message": "Change your temporary password to continue.",
            "details": {},
        }
        assert allowed.status_code == 200
        assert allowed.json()["must_change_password"] is True

    @pytest.mark.urls("tests.testapp.urls")
    def test_other_modules_endpoints_are_gated_too(self, logged_in):
        _, tokens = logged_in("student", must_change_password=True)

        response = bearer(tokens["access"]).get("/api/v1/test/notes/")

        assert response.status_code == 403
        assert response.json()["code"] == "password_change_required"

    def test_the_public_schema_ignores_the_token(self, logged_in):
        _, tokens = logged_in("student", must_change_password=True)

        assert bearer(tokens["access"]).get("/api/v1/schema/").status_code == 200

    def test_changing_the_password_opens_the_api(self, logged_in):
        _, tokens = logged_in("student", must_change_password=True)

        response = bearer(tokens["access"]).post(
            "/api/v1/me/password/",
            {"current_password": PASSWORD, "new_password": "Brand-New-Pass-77"},
            format="json",
        )

        assert response.status_code == 200
        client = bearer(response.json()["access"])
        assert client.get("/api/v1/me/").json()["must_change_password"] is False
        device = client.post("/api/v1/me/devices/", {"platform": "ios", "token": "t"})
        assert device.status_code == 201


class TestChangePassword:
    def change(self, access, current=PASSWORD, new="Brand-New-Pass-77", language="en"):
        return bearer(access, language=language).post(
            "/api/v1/me/password/",
            {"current_password": current, "new_password": new},
            format="json",
        )

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_each_role_can_change_their_password(self, logged_in, role):
        user, tokens = logged_in(role)

        response = self.change(tokens["access"])

        assert response.status_code == 200
        assert login(user.username, "Brand-New-Pass-77").status_code == 200
        assert login(user.username, PASSWORD).status_code == 400
        assert AuditLog.objects.filter(action="password_change", user_id=user.pk).exists()

    def test_old_tokens_stop_working(self, logged_in):
        _, tokens = logged_in("student")

        self.change(tokens["access"])

        assert bearer(tokens["access"]).get("/api/v1/me/").status_code == 401
        refresh = APIClient().post(
            "/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        assert refresh.json()["code"] == "token_invalid"

    def test_wrong_current_password(self, logged_in):
        _, tokens = logged_in("student")

        response = self.change(tokens["access"], current="not-it")

        assert response.status_code == 400
        assert response.json()["code"] == "wrong_password"

    def test_password_rules_from_django_validators(self, logged_in):
        _, tokens = logged_in("student")

        response = self.change(tokens["access"], new="12345678", language="ar")

        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "password_invalid"
        assert body["message"] == "كلمة المرور الجديدة لا تحقق قواعد كلمات المرور."
        assert len(body["details"]["messages"]) >= 2  # too common and entirely numeric

    def test_a_password_like_the_username_is_refused(self, logged_in):
        _, tokens = logged_in("student", username="sara.ali.hasan")

        response = self.change(tokens["access"], new="sara.ali.hasan1")

        assert response.json()["code"] == "password_invalid"

    def test_not_logged_in(self):
        response = APIClient().post("/api/v1/me/password/", {}, format="json")

        assert response.status_code == 401


class TestDevices:
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_each_role_registers_a_device(self, logged_in, role):
        user, tokens = logged_in(role)

        response = bearer(tokens["access"]).post(
            "/api/v1/me/devices/", {"platform": "android", "token": "fcm-1"}, format="json"
        )

        assert response.status_code == 201
        assert response.json()["platform"] == "android"
        assert DeviceToken.objects.get(token="fcm-1").user_id == user.pk

    def test_invalid_platform(self, logged_in):
        _, tokens = logged_in("student")

        response = bearer(tokens["access"]).post(
            "/api/v1/me/devices/", {"platform": "nokia", "token": "x"}, format="json"
        )

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_not_logged_in(self):
        response = APIClient().post("/api/v1/me/devices/", {}, format="json")

        assert response.status_code == 401
