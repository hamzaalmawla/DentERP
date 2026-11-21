"""Who sees and opens which dashboard screen (DB-01, DB-21 access part, design sections 8
and 11). The notes screen of ``tests.testapp`` stands for a Patients screen: super admin and
reception change it, management only reads it, supervisors do not see it."""

import pytest
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ImproperlyConfigured
from django.utils import translation

from apps.accounts.dashboard import (
    GROUP_TITLES,
    ROLE_GROUPS,
    Group,
    ReadOnlyForManagement,
    navigation,
)
from apps.accounts.dashboard.navigation import register_screen
from apps.accounts.dashboard.site import DashboardSite
from apps.core.dashboard import DashboardModelAdmin
from apps.core.models import AuditLog
from tests.testapp.models import Note

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

DASHBOARD_ROLES = ["super_admin", "management", "reception", "supervisor"]
USERS_SCREENS = [
    "/dashboard/accounts/user/",
    "/dashboard/accounts/user/add/",
    "/dashboard/accounts/role/",
    "/dashboard/core/auditlog/",
]


@pytest.fixture
def every_group():
    """One screen in every sidebar group, for the duration of the test."""
    saved = list(navigation._screens)
    for group in Group:
        register_screen(group, url_name="admin:index", title=f"screen {group}", icon="circle")
    yield
    navigation._screens[:] = saved


def sidebar_groups(response) -> set[str]:
    with translation.override("en"):
        return {str(group["title"]) for group in response.context["sidebar_navigation"]}


def group_titles(groups) -> set[str]:
    with translation.override("en"):
        return {str(GROUP_TITLES[group]) for group in groups}


# --- The sidebar ----------------------------------------------------------------------


@pytest.mark.parametrize("role", DASHBOARD_ROLES)
def test_each_role_sees_only_its_own_groups(dashboard, every_group, role):
    response = dashboard(role).get("/dashboard/")

    assert sidebar_groups(response) == group_titles(ROLE_GROUPS[role])


def test_the_role_map_follows_the_design():
    assert ROLE_GROUPS["super_admin"] == frozenset(Group)
    assert ROLE_GROUPS["management"] == {
        Group.HOME,
        Group.PATIENTS,
        Group.CLINICAL,
        Group.SCHEDULING,
        Group.MAINTENANCE,
        Group.REPORTS,
    }
    assert ROLE_GROUPS["reception"] == {Group.PATIENTS}
    assert ROLE_GROUPS["supervisor"] == {
        Group.HOME,
        Group.APPROVALS,
        Group.CLINICAL,
        Group.SCHEDULING,
        Group.STUDENTS,
        Group.REPORTS,
        Group.MAINTENANCE,
    }
    assert set(ROLE_GROUPS) == set(DASHBOARD_ROLES)


def test_empty_groups_are_hidden(dashboard):
    response = dashboard("supervisor").get("/dashboard/")

    assert sidebar_groups(response) == group_titles({Group.HOME})


def test_the_super_admin_sees_the_users_group(dashboard):
    response = dashboard("super_admin").get("/dashboard/")

    links = [
        item["link"] for group in response.context["sidebar_navigation"] for item in group["items"]
    ]
    assert set(USERS_SCREENS) - {"/dashboard/accounts/user/add/"} <= set(links)


def test_a_screen_can_be_narrowed_to_some_roles_of_its_group(dashboard, every_group):
    register_screen(Group.PATIENTS, model="testapp.Note", title="x", icon="x", roles=["reception"])

    assert navigation.model_roles(Note) == {"super_admin", "management", "reception"}
    register_screen(Group.REPORTS, model="core.AuditLog", title="x", icon="x", roles=["student"])
    assert "student" not in navigation.model_roles(AuditLog)


# --- The role check on every view -----------------------------------------------------


@pytest.mark.parametrize("role", ["management", "reception", "supervisor"])
@pytest.mark.parametrize("url", USERS_SCREENS)
def test_only_the_super_admin_opens_the_users_screens_by_url(dashboard, make_user, role, url):
    assert dashboard(role).get(url).status_code == 403


@pytest.mark.parametrize("url", USERS_SCREENS)
def test_the_super_admin_opens_the_users_screens(dashboard, url):
    assert dashboard("super_admin").get(url).status_code == 200


def test_a_supervisor_cannot_open_a_user_by_url(dashboard, make_user):
    other = make_user("other", "student")
    client = dashboard("supervisor")

    assert client.get(f"/dashboard/accounts/user/{other.pk}/change/").status_code == 403
    assert client.get(f"/dashboard/accounts/user/{other.pk}/reset-password/").status_code == 403
    response = client.post(f"/dashboard/accounts/user/{other.pk}/deactivate/")
    assert response.status_code == 403
    other.refresh_from_db()
    assert other.is_active


@pytest.mark.parametrize("role", ["student", "technician"])
def test_students_and_technicians_have_no_dashboard_even_with_a_session(dashboard, role):
    client = dashboard(role)

    response = client.get("/dashboard/accounts/user/")

    assert response.status_code == 302
    assert response["Location"].startswith("/dashboard/login/")


def test_the_super_admin_acting_as_supervisor_cannot_manage_users(dashboard):
    client = dashboard("super_admin", "supervisor")
    client.post("/dashboard/role/", {"role": "supervisor"})

    assert client.get("/dashboard/accounts/user/").status_code == 403

    client.post("/dashboard/role/", {"role": "super_admin"})
    assert client.get("/dashboard/accounts/user/").status_code == 200


# --- Management reads, never changes (ReadOnlyForManagement) --------------------------


@pytest.fixture
def note():
    return Note.objects.create(title="old")


def test_management_sees_the_screen_read_only(dashboard, note):
    client = dashboard("management")

    assert client.get("/dashboard/testapp/note/").status_code == 200
    response = client.get(f"/dashboard/testapp/note/{note.pk}/change/")
    assert response.status_code == 200
    assert response.context["has_change_permission"] is False
    assert response.context["has_add_permission"] is False


def test_management_cannot_save(dashboard, note):
    client = dashboard("management")

    response = client.post(f"/dashboard/testapp/note/{note.pk}/change/", {"title": "new"})

    assert response.status_code == 403
    note.refresh_from_db()
    assert note.title == "old"
    assert client.get("/dashboard/testapp/note/add/").status_code == 403
    assert client.post("/dashboard/testapp/note/add/", {"title": "x"}).status_code == 403
    assert Note.objects.count() == 1


@pytest.mark.parametrize("role", ["super_admin", "reception"])
def test_roles_that_change_the_screen_can_save(dashboard, note, role):
    client = dashboard(role)

    response = client.post(f"/dashboard/testapp/note/{note.pk}/change/", {"title": "new"})

    assert response.status_code == 302
    note.refresh_from_db()
    assert note.title == "new"


def test_a_supervisor_does_not_see_a_screen_outside_their_groups(dashboard, note):
    assert dashboard("supervisor").get("/dashboard/testapp/note/").status_code == 403


def test_nothing_is_ever_deleted_from_the_dashboard(dashboard, note):
    client = dashboard("super_admin")

    assert client.get(f"/dashboard/testapp/note/{note.pk}/delete/").status_code == 403
    response = client.get("/dashboard/testapp/note/")
    actions = response.context["cl"].model_admin.get_actions(response.wsgi_request)
    assert "delete_selected" not in actions


# --- What the site accepts -------------------------------------------------------------


def test_the_site_adds_read_only_for_management_to_every_screen():
    site = DashboardSite(name="check")

    class PlainAdmin(DashboardModelAdmin):
        pass

    site.register(Note, PlainAdmin)

    assert isinstance(site._registry[Note], ReadOnlyForManagement)


def test_the_site_refuses_a_module_screen_without_the_role_check():
    site = DashboardSite(name="check")
    unchecked = type("UncheckedAdmin", (ModelAdmin,), {"__module__": "apps.somewhere.admin"})

    with pytest.raises(ImproperlyConfigured):
        site.register(Note, unchecked)


def test_library_screens_are_left_out():
    site = DashboardSite(name="check")
    library = type("LibraryAdmin", (ModelAdmin,), {"__module__": "some_library.admin"})

    site.register(Note, library)

    assert not site.is_registered(Note)


def test_only_dashboard_screens_are_registered():
    from django.contrib import admin

    assert all(isinstance(a, DashboardModelAdmin) for a in admin.site._registry.values())
    labels = {model._meta.label for model in admin.site._registry}
    assert {"accounts.User", "accounts.Role", "core.AuditLog"} <= labels
    assert "auth.Group" not in labels


# --- The gates ----------------------------------------------------------------------------


@pytest.mark.parametrize("url", ["/dashboard/", "/dashboard/accounts/user/", "/dashboard/role/"])
def test_a_temporary_password_must_be_changed_first(dashboard, url):
    client = dashboard("super_admin", must_change_password=True)

    response = client.get(url)

    assert response.status_code == 302
    assert response["Location"] == "/dashboard/password_change/"


def test_changing_the_password_opens_the_dashboard(dashboard):
    client = dashboard("super_admin", must_change_password=True)

    response = client.post(
        "/dashboard/password_change/",
        {
            "old_password": PASSWORD,
            "new_password1": "Brand-New-Pass-77",
            "new_password2": "Brand-New-Pass-77",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/dashboard/password_change/done/"
    client.user.refresh_from_db()
    assert client.user.must_change_password is False
    assert client.user.check_password("Brand-New-Pass-77")
    assert AuditLog.objects.filter(action="password_change", user=client.user).exists()
    assert client.get("/dashboard/").status_code == 200  # still logged in


@pytest.mark.parametrize(
    ("values", "field", "message"),
    [
        ({"old_password": "wrong"}, "old_password", "The current password is incorrect."),
        ({"new_password2": "Other-Pass-2026"}, "new_password2", "are not the same"),
        (
            {"new_password1": PASSWORD, "new_password2": PASSWORD},
            "new_password1",
            "must be different",
        ),
        ({"new_password1": "12345678", "new_password2": "12345678"}, "new_password1", "rules"),
    ],
)
def test_password_change_errors(dashboard, values, field, message):
    client = dashboard("super_admin", must_change_password=True)
    data = {
        "old_password": PASSWORD,
        "new_password1": "Brand-New-Pass-77",
        "new_password2": "Brand-New-Pass-77",
        **values,
    }

    response = client.post("/dashboard/password_change/", data)

    assert response.status_code == 200
    assert any(message in error for error in response.context["form"].errors[field])
    client.user.refresh_from_db()
    assert client.user.must_change_password is True


def test_a_user_with_several_dashboard_roles_chooses_one(dashboard):
    client = dashboard("super_admin", "supervisor")

    response = client.get("/dashboard/accounts/user/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/role/"

    page = client.get("/dashboard/role/")
    assert [code for code, _name in page.context["roles"]] == ["super_admin", "supervisor"]
    assert client.post("/dashboard/role/", {"role": "super_admin"})["Location"] == "/dashboard/"
    assert client.get("/dashboard/accounts/user/").status_code == 200


def test_a_student_role_does_not_count_as_a_dashboard_role(dashboard):
    client = dashboard("student", "supervisor")

    assert client.get("/dashboard/").status_code == 200  # no choice: supervisor is the only one


def test_a_role_not_held_cannot_be_chosen(dashboard):
    client = dashboard("supervisor", "reception")

    assert client.post("/dashboard/role/", {"role": "super_admin"}).status_code == 403
    assert client.post("/dashboard/role/", {"role": "student"}).status_code == 403


def test_choosing_a_role_returns_to_a_safe_next_page(dashboard):
    client = dashboard("super_admin", "supervisor")

    local = client.post(
        "/dashboard/role/", {"role": "super_admin", "next": "/dashboard/core/auditlog/"}
    )
    outside = client.post(
        "/dashboard/role/", {"role": "super_admin", "next": "https://evil.example/"}
    )

    assert local["Location"] == "/dashboard/core/auditlog/"
    assert outside["Location"] == "/dashboard/"


def test_the_account_menu_offers_switching_role(dashboard):
    two = dashboard("super_admin", "supervisor")
    two.post("/dashboard/role/", {"role": "supervisor"})
    one = dashboard("supervisor", username="only_one")

    assert two.get("/dashboard/").context["account_links"][0]["link"] == "/dashboard/role/"
    assert one.get("/dashboard/").context["account_links"] == []


# --- Language -----------------------------------------------------------------------------


def test_arabic_right_to_left_by_default_whatever_the_browser_says(client):
    response = client.get("/dashboard/login/", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    assert '<html lang="ar" dir="rtl"' in response.content.decode()


def test_the_language_switch_changes_the_dashboard_language(client):
    response = client.post("/i18n/setlang/", {"language": "en", "next": "/dashboard/login/"})
    assert response.status_code == 302

    page = client.get("/dashboard/login/")

    assert '<html lang="en" dir="ltr"' in page.content.decode()


def test_the_api_still_follows_accept_language(client):
    response = client.get("/api/v1/me/", HTTP_ACCEPT_LANGUAGE="en")

    assert response.json()["message"].startswith("Authentication credentials")
