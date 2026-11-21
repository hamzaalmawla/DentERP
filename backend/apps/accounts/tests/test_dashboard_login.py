"""Dashboard login (DB-01, SYS-01, design section 8): the same rules as the API login, through
``VerifyCredentials`` and ``DashboardBackend``."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import authenticate
from django.test import Client
from django.utils import timezone

from apps.accounts.testing.api import login as api_login
from apps.core.models import AuditLog

from .conftest import PASSWORD, english_client

pytestmark = pytest.mark.django_db

LOGIN = "/dashboard/login/"


def post_login(client, username="sara", password=PASSWORD):
    return client.post(LOGIN, {"username": username, "password": password})


def page_text(response) -> str:
    return response.content.decode()


@pytest.mark.parametrize("role", ["super_admin", "management", "reception", "supervisor"])
def test_dashboard_roles_log_in_and_the_login_is_audited(make_user, role):
    user = make_user("sara", role)
    client = english_client()

    response = post_login(client, " Sara ")

    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"
    assert client.get("/dashboard/", follow=True).status_code == 200
    entry = AuditLog.objects.get(action="login")
    assert (entry.user_id, entry.object_id) == (user.pk, str(user.pk))
    user.refresh_from_db()
    assert user.last_login is not None


@pytest.mark.parametrize("role", ["student", "technician"])
def test_students_and_technicians_get_a_clear_message(make_user, role):
    user = make_user("sara", role)
    client = english_client()

    response = post_login(client)

    assert response.status_code == 200
    assert "use the mobile app" in page_text(response)
    assert "_auth_user_id" not in client.session
    entry = AuditLog.objects.get(action="login_failed")
    assert entry.user_id == user.pk
    assert entry.changes == {"username": "sara", "reason": "dashboard_not_allowed"}


def test_a_student_who_is_also_a_supervisor_logs_in(make_user):
    make_user("sara", "student", "supervisor")

    assert post_login(english_client()).status_code == 302


def test_wrong_password_is_refused_and_counted(make_user):
    user = make_user("sara", "supervisor")

    response = post_login(english_client(), password="wrong")

    assert "The username or password is incorrect." in page_text(response)
    user.refresh_from_db()
    assert user.failed_logins == 1
    assert AuditLog.objects.get(action="login_failed").changes["reason"] == "wrong_password"


def test_five_failures_lock_the_account_for_the_dashboard_and_the_api(make_user):
    make_user("sara", "supervisor")
    client = english_client()
    for _ in range(4):
        post_login(client, password="wrong")

    response = post_login(client, password="wrong")

    assert "The account is locked" in page_text(response)
    # The right password is refused while locked, here and in the API: one lockout.
    assert "The account is locked" in page_text(post_login(client))
    assert api_login("sara", PASSWORD).json()["code"] == "account_locked"


def test_an_api_lockout_also_closes_the_dashboard(make_user):
    make_user("sara", "supervisor", locked_until=timezone.now() + timedelta(minutes=10))

    response = post_login(english_client())

    assert "The account is locked" in page_text(response)
    assert AuditLog.objects.get(action="login_failed").changes["reason"] == "locked"


def test_a_user_without_a_role_is_refused(make_user):
    make_user("sara")

    response = post_login(english_client())

    assert "no role yet" in page_text(response)


def test_a_deactivated_user_is_refused(make_user):
    make_user("sara", "super_admin").deactivate()

    response = post_login(english_client())

    assert response.status_code == 200
    assert "The username or password is incorrect." in page_text(response)


def test_the_messages_are_in_arabic_by_default(make_user):
    make_user("sara", "student")
    browser_in_english = Client(HTTP_ACCEPT_LANGUAGE="en")  # the browser's language is ignored

    response = post_login(browser_in_english)

    assert "تطبيق الهاتف" in page_text(response)


def test_the_dashboard_backend_is_the_only_one():
    assert settings.AUTHENTICATION_BACKENDS == ["apps.accounts.dashboard.backends.DashboardBackend"]


def test_the_backend_returns_the_user_or_nothing(make_user):
    user = make_user("sara", "supervisor")

    assert authenticate(None, username="SARA", password=PASSWORD) == user
    assert authenticate(None, username="sara", password="wrong") is None
    assert authenticate(None, username="sara") is None


def test_sessions_end_after_two_idle_hours():
    assert settings.SESSION_COOKIE_AGE == 2 * 60 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_a_deactivated_user_is_logged_out(dashboard):
    client = dashboard("supervisor")
    client.user.deactivate()

    response = client.get("/dashboard/")

    assert response.status_code == 302
    assert response["Location"].startswith(LOGIN)


def test_a_user_whose_dashboard_roles_were_removed_is_logged_out(dashboard):
    client = dashboard("supervisor", "student")
    client.user.user_roles.filter(role__code="supervisor").deactivate()

    response = client.get("/dashboard/")

    assert response.status_code == 302
    assert response["Location"].startswith(LOGIN)
