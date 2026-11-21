"""US-04 (backend part): "As any user, I want to log in once and land in my own interface."

The app picks the interface from the roles the login returns; the server makes sure each
interface only reaches its own endpoints (ST-01, SYS-01, SYS-02).
"""

import pytest
from django.test import Client
from django.utils import translation

from apps.accounts.dashboard import GROUP_TITLES, ROLE_GROUPS
from apps.accounts.testing.api import bearer, login

from .conftest import PASSWORD

pytestmark = [pytest.mark.django_db, pytest.mark.urls("apps.accounts.tests.urls")]


@pytest.mark.parametrize("role", ["student", "supervisor", "technician"])
def test_us04_a_user_with_one_role_lands_in_that_interface(make_user, role):
    make_user("sara", role)

    body = login("sara", PASSWORD).json()
    client = bearer(body["access"])

    assert body["roles"] == [role]
    assert client.get("/api/v1/me/").json()["active_role"] == role
    assert client.get(f"/api/v1/test/{role}/").status_code == 200


def test_us04_a_user_with_two_roles_chooses_one(make_user):
    make_user("sara", "student", "supervisor")

    body = login("sara", PASSWORD).json()

    assert body["roles"] == ["student", "supervisor"]
    unchosen = bearer(body["access"])
    assert unchosen.get("/api/v1/me/").json()["active_role"] is None
    assert unchosen.get("/api/v1/test/student/").json()["code"] == "active_role_required"
    chosen = bearer(body["access"], role="student")
    assert chosen.get("/api/v1/me/").json()["active_role"] == "student"
    assert chosen.get("/api/v1/test/student/").status_code == 200
    assert chosen.get("/api/v1/test/supervisor/").status_code == 403


def test_us04_messages_are_in_arabic_by_default(make_user):
    make_user("sara", "student")

    response = login("sara", "wrong", language="")

    assert response.json()["message"] == "اسم المستخدم أو كلمة المرور غير صحيحة."


def test_us04_the_first_login_asks_for_a_new_password(make_user):
    make_user("sara", "student", must_change_password=True)

    body = login("sara", PASSWORD).json()

    assert body["must_change_password"] is True
    blocked = bearer(body["access"]).get("/api/v1/test/student/")
    assert blocked.json()["code"] == "password_change_required"


# --- Dashboard part (DB-21 access) ------------------------------------------------------

DASHBOARD_LOGIN = "/dashboard/login/"


def _dashboard_login(username: str):
    client = Client()
    response = client.post(DASHBOARD_LOGIN, {"username": username, "password": PASSWORD})
    return client, response


@pytest.mark.urls("config.urls")
@pytest.mark.parametrize("role", ["reception", "supervisor"])
def test_us04_reception_and_supervisors_log_in_to_the_dashboard_and_see_only_their_menus(
    make_user, role
):
    make_user("sara", role)

    client, response = _dashboard_login("sara")
    page = client.get("/dashboard/", follow=True)

    assert response.status_code == 302
    assert page.status_code == 200
    with translation.override("en"):
        shown = {str(group["title"]) for group in page.context["sidebar_navigation"]}
        allowed = {str(GROUP_TITLES[group]) for group in ROLE_GROUPS[role]}
    assert shown <= allowed
    assert client.get("/dashboard/accounts/user/").status_code == 403


@pytest.mark.urls("config.urls")
@pytest.mark.parametrize("role", ["student", "technician"])
def test_us04_students_and_technicians_cannot_log_in_to_the_dashboard(make_user, role):
    make_user("sara", role)

    client, response = _dashboard_login("sara")

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert "تطبيق الهاتف" in response.content.decode()  # "use the mobile app", in Arabic


@pytest.mark.urls("config.urls")
def test_us04_every_dashboard_screen_is_arabic_right_to_left_by_default(make_user):
    make_user("sara", "super_admin")
    login_page = Client().get(DASHBOARD_LOGIN, HTTP_ACCEPT_LANGUAGE="en").content.decode()
    assert '<html lang="ar" dir="rtl"' in login_page
    client, _ = _dashboard_login("sara")

    for url in [
        "/dashboard/",
        "/dashboard/accounts/user/",
        "/dashboard/accounts/user/add/",
        "/dashboard/accounts/role/",
        "/dashboard/core/auditlog/",
        "/dashboard/password_change/",
    ]:
        html = client.get(url, HTTP_ACCEPT_LANGUAGE="en").content.decode()
        assert '<html lang="ar" dir="rtl"' in html, url
