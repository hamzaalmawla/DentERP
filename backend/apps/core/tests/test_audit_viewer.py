"""The audit log viewer (DB-17): read-only, filtered by user, record type, action and date.
Who opens it comes from the dashboard's role map (system administrator only)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Role, User, UserRole
from apps.core.dashboard import DashboardModelAdmin
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

URL = "/dashboard/core/auditlog/"


def logged_in(username: str, role: str) -> tuple[Client, User]:
    user = User.objects.create_user(username, "Strong-Pass-2026", full_name_ar=username)
    UserRole.objects.create(user=user, role=Role.objects.get(code=role))
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def entries():
    _, sara = logged_in("sara", "student")
    now = timezone.now()
    return [
        AuditLog.objects.create(user=sara, action="login", model="accounts.User", object_id="1"),
        AuditLog.objects.create(
            user=None,
            action="create",
            model="testapp.Note",
            object_id="7",
            at=now - timedelta(days=10),
        ),
        AuditLog.objects.create(user=sara, action="update", model="testapp.Note", object_id="7"),
    ]


def ids(response) -> set[int]:
    return {entry.pk for entry in response.context["cl"].result_list}


def test_filters_by_user_record_type_action_and_date(entries):
    client, _ = logged_in("admin", "super_admin")
    login, create, update = entries
    sara = login.user
    today = timezone.localdate()

    assert ids(client.get(URL)) >= {login.pk, create.pk, update.pk}
    assert ids(client.get(f"{URL}?user__id__exact={sara.pk}")) == {login.pk, update.pk}
    assert ids(client.get(f"{URL}?model=testapp.Note")) == {create.pk, update.pk}
    assert ids(client.get(f"{URL}?action=create")) == {create.pk}
    # Both days are included, in the clinic's time zone.
    recent = client.get(f"{URL}?at_from={today - timedelta(days=1)}&at_to={today}")
    assert ids(recent) == {login.pk, update.pk}
    ten_days_ago = timezone.localdate(create.at)
    old = client.get(f"{URL}?at_from={ten_days_ago}&at_to={ten_days_ago}")
    assert ids(old) == {create.pk}
    assert ids(client.get(f"{URL}?at_from=not-a-date")) == set()
    assert ids(client.get(f"{URL}?q=7")) == {create.pk, update.pk}


def test_the_filter_choices_come_from_the_log(entries):
    client, _ = logged_in("admin", "super_admin")

    response = client.get(URL)

    filters = {
        spec.parameter_name: spec
        for spec in response.context["cl"].filter_specs
        if hasattr(spec, "parameter_name")
    }
    assert {"login", "create", "update"} <= {v for v, _ in filters["action"].lookup_choices}
    assert {"accounts.User", "testapp.Note"} <= {v for v, _ in filters["model"].lookup_choices}


def test_read_only(entries):
    client, _ = logged_in("admin", "super_admin")
    entry = entries[0]

    page = client.get(f"{URL}{entry.pk}/change/")

    assert page.status_code == 200
    assert page.context["has_change_permission"] is False
    assert client.post(f"{URL}{entry.pk}/change/", {"action": "x"}).status_code == 403
    assert client.get(f"{URL}add/").status_code == 403
    assert client.get(f"{URL}{entry.pk}/delete/").status_code == 403
    entry.refresh_from_db()
    assert entry.action == "login"


@pytest.mark.parametrize("role", ["management", "reception", "supervisor"])
def test_only_the_system_administrator_opens_it(entries, role):
    client, _ = logged_in("other", role)

    assert client.get(URL).status_code == 403


def test_the_base_screen_opens_nothing_on_a_plain_admin_site():
    from django.contrib.admin import AdminSite
    from django.test import RequestFactory

    admin = DashboardModelAdmin(AuditLog, AdminSite())
    request = RequestFactory().get("/")

    assert not admin.has_view_permission(request)
    assert not admin.has_module_permission(request)
    assert not admin.has_delete_permission(request)
