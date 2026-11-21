"""POST /auth/login/, /auth/refresh/ and /auth/logout/ with real tokens."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.testing.api import bearer, login
from apps.core.models import AuditLog

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def post(path: str, body: dict, language: str = "en"):
    return APIClient().post(path, body, format="json", HTTP_ACCEPT_LANGUAGE=language)


class TestLogin:
    @pytest.mark.parametrize(
        "role", ["super_admin", "management", "reception", "supervisor", "student", "technician"]
    )
    def test_every_role_can_log_in(self, make_user, role):
        make_user("sara", role)

        response = login("sara", PASSWORD)

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"access", "refresh", "must_change_password", "roles"}
        assert body["roles"] == [role]
        assert body["must_change_password"] is False

    def test_the_access_token_opens_the_api(self, make_user):
        make_user("sara", "student")
        access = login("sara", PASSWORD).json()["access"]

        assert bearer(access).get("/api/v1/me/").status_code == 200

    def test_login_is_audited_with_the_ip(self, make_user):
        user = make_user("sara", "student")

        login("sara", PASSWORD)

        entry = AuditLog.objects.get(action="login")
        assert (entry.user_id, entry.object_id, entry.ip) == (user.pk, str(user.pk), "127.0.0.1")

    def test_wrong_password(self, make_user):
        user = make_user("sara", "student")

        response = login("sara", "wrong-password")

        assert response.status_code == 400
        assert response.json() == {
            "code": "invalid_credentials",
            "message": "The username or password is incorrect.",
            "details": {},
        }
        user.refresh_from_db()
        assert user.failed_logins == 1
        assert AuditLog.objects.get(action="login_failed").user_id == user.pk

    def test_wrong_password_in_arabic(self, make_user):
        make_user("sara", "student")

        response = login("sara", "wrong-password", language="ar")

        assert response.json()["message"] == "اسم المستخدم أو كلمة المرور غير صحيحة."

    def test_unknown_user_gets_the_same_answer(self):
        response = login("nobody", PASSWORD)

        assert response.status_code == 400
        assert response.json()["code"] == "invalid_credentials"
        assert AuditLog.objects.get(action="login_failed").user_id is None

    def test_missing_fields(self):
        response = post("/api/v1/auth/login/", {"username": "sara"})

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"
        assert "password" in response.json()["details"]

    def test_lockout_after_five_failures_and_unlock(self, make_user):
        from apps.accounts import container
        from apps.core.application.dtos import Actor

        user = make_user("sara", "student")
        admin = make_user("admin", "super_admin")
        for _ in range(4):
            assert login("sara", "wrong").json()["code"] == "invalid_credentials"

        fifth = login("sara", "wrong")
        locked = login("sara", PASSWORD)  # the right password is refused while locked

        assert fifth.status_code == 403
        assert fifth.json()["code"] == "account_locked"
        assert locked.json()["code"] == "account_locked"
        user.refresh_from_db()
        assert user.locked_until > timezone.now() + timedelta(minutes=14)
        assert "locked_until" in locked.json()["details"]

        container.unlock_account().execute(Actor(admin.pk, "super_admin"), user.pk)

        assert login("sara", PASSWORD).status_code == 200
        assert AuditLog.objects.filter(action="unlock", object_id=str(user.pk)).exists()

    def test_the_lock_ends_after_15_minutes(self, make_user):
        user = make_user("sara", "student")
        User.objects.filter(pk=user.pk).update(
            failed_logins=5, locked_until=timezone.now() - timedelta(seconds=1)
        )

        assert login("sara", PASSWORD).status_code == 200

    def test_a_bad_authorization_header_does_not_block_login(self, make_user):
        make_user("sara", "student")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer expired-or-garbage")

        assert login("sara", PASSWORD, client=client).status_code == 200

    def test_ten_logins_a_minute_per_ip(self, make_user):
        make_user("sara", "student")
        for _ in range(10):
            login("nobody", "x")

        response = login("sara", PASSWORD)

        assert response.status_code == 429
        assert response.json()["code"] == "throttled"
        assert "Retry-After" in response


class TestRefresh:
    def test_rotation(self, logged_in):
        _, tokens = logged_in("student")

        response = post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

        assert response.status_code == 200
        pair = response.json()
        assert set(pair) == {"access", "refresh"}
        assert pair["refresh"] != tokens["refresh"]
        assert bearer(pair["access"]).get("/api/v1/me/").status_code == 200

    def test_a_rotated_refresh_token_is_refused(self, logged_in):
        _, tokens = logged_in("student")
        post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

        response = post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

        assert response.status_code == 400
        assert response.json()["code"] == "token_invalid"

    def test_an_access_token_is_not_a_refresh_token(self, logged_in):
        _, tokens = logged_in("student")

        response = post("/api/v1/auth/refresh/", {"refresh": tokens["access"]})

        assert response.json()["code"] == "token_invalid"

    def test_garbage(self):
        response = post("/api/v1/auth/refresh/", {"refresh": "garbage"}, language="ar")

        assert response.status_code == 400
        assert response.json()["message"] == "انتهت الجلسة. سجّل الدخول مرة أخرى."

    def test_a_deactivated_user_cannot_refresh(self, logged_in):
        user, tokens = logged_in("student")
        user.deactivate()

        response = post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})

        assert response.json()["code"] == "token_invalid"


class TestLogout:
    def test_logout_blacklists_the_refresh_token(self, logged_in):
        user, tokens = logged_in("student")

        response = post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

        assert response.status_code == 204
        refused = post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
        assert refused.json()["code"] == "token_invalid"
        assert AuditLog.objects.filter(action="logout", user_id=user.pk).exists()

    def test_logout_twice(self, logged_in):
        _, tokens = logged_in("student")
        post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

        response = post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

        assert response.json()["code"] == "token_invalid"

    def test_logout_works_while_the_password_must_change(self, logged_in):
        _, tokens = logged_in("student", must_change_password=True)
        client = bearer(tokens["access"])

        response = client.post(
            "/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )

        assert response.status_code == 204
