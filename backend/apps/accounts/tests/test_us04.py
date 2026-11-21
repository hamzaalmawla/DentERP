"""US-04 (backend part): "As any user, I want to log in once and land in my own interface."

The app picks the interface from the roles the login returns; the server makes sure each
interface only reaches its own endpoints (ST-01, SYS-01, SYS-02).
"""

import pytest

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
