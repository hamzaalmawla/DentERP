"""CreateDemoUsers service and the create_demo_users command."""

import pytest
from django.core.management import CommandError, call_command

from apps.accounts.application.services import CreateDemoUsers
from apps.accounts.models import User
from apps.accounts.testing.api import login


def demo(f, password="Demo-Pass-2026"):
    return CreateDemoUsers(f.accounts, f.roles, f.hasher, f.audit, f.uow).execute(password)


def test_creates_one_user_per_role(fakes):
    created = demo(fakes)

    assert [user.role for user in created] == [
        "super_admin",
        "management",
        "reception",
        "supervisor",
        "student",
        "technician",
    ]
    assert fakes.accounts.roles_of(fakes.accounts.get_by_username("demo_student").id) == {"student"}
    assert fakes.accounts.get_by_username("demo_student").must_change_password is False
    assert fakes.audit.actions() == ["create"] * 6


def test_running_again_changes_nothing(fakes):
    demo(fakes)

    assert demo(fakes) == []
    assert len(fakes.accounts.users) == 6


def test_the_command_creates_users_that_can_log_in(db):
    call_command("create_demo_users", "--password", "Demo-Pass-2026")

    assert User.objects.filter(username__startswith="demo_").count() == 6
    response = login("demo_technician", "Demo-Pass-2026")
    assert response.status_code == 200
    assert response.json()["roles"] == ["technician"]


def test_the_command_refuses_outside_development(db, settings):
    settings.DEMO_USERS_ALLOWED = False

    with pytest.raises(CommandError, match="development only"):
        call_command("create_demo_users")

    assert not User.objects.exists()
