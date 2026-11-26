"""A user's department (DB-02): CreateUser and UpdateUser check it through the setup facade,
and the user screens offer the active departments."""

import pytest

from apps.accounts.application.services import (
    CreateUser,
    CreateUserCommand,
    UpdateUser,
    UpdateUserCommand,
)
from apps.accounts.models import User
from apps.core.application.dtos import Actor
from apps.core.domain.errors import DomainError
from apps.setup.application.dtos import DepartmentDTO
from apps.setup.models import Department


@pytest.fixture
def admin(fakes) -> Actor:
    account = fakes.accounts.add("admin", roles=("super_admin",))
    return Actor(account.id, "super_admin")


@pytest.fixture
def endo(fakes) -> DepartmentDTO:
    return fakes.setup.add_department(DepartmentDTO(4, "اللبية", "Endodontics"))


def create(f, actor, **values):
    values = {"username": "sara", "full_name_ar": "سارة", "roles": ["supervisor"], **values}
    return CreateUser(f.accounts, f.roles, f.setup, f.hasher, f.passwords, f.audit, f.uow).execute(
        actor, CreateUserCommand(**values)
    )


def update(f, actor, user_id, **values):
    values = {"full_name_ar": "سارة", **values}
    return UpdateUser(f.accounts, f.setup, f.audit, f.uow).execute(
        actor, UpdateUserCommand(user_id=user_id, **values)
    )


class TestServices:
    def test_create_with_a_department(self, fakes, admin, endo):
        result = create(fakes, admin, department_id=endo.id)

        assert result.user.department_id == endo.id
        assert fakes.audit.entries[-1].changes["department_id"] == {"old": None, "new": endo.id}

    def test_create_without_a_department(self, fakes, admin):
        assert create(fakes, admin).user.department_id is None

    def test_create_with_an_unknown_or_deactivated_department(self, fakes, admin):
        with pytest.raises(DomainError) as error:
            create(fakes, admin, department_id=99)

        assert error.value.code == "department_not_found"
        assert not fakes.accounts.username_exists("sara")

    def test_change_the_department(self, fakes, admin, endo):
        user = fakes.accounts.add("sara", full_name_ar="سارة")

        result = update(fakes, admin, user.id, department_id=endo.id)

        assert result.department_id == endo.id
        assert fakes.audit.entries[-1].changes == {"department_id": {"old": None, "new": endo.id}}

    def test_change_to_an_unknown_department(self, fakes, admin):
        user = fakes.accounts.add("sara", full_name_ar="سارة")

        with pytest.raises(DomainError) as error:
            update(fakes, admin, user.id, department_id=99)

        assert error.value.code == "department_not_found"

    def test_a_department_deactivated_since_can_be_kept(self, fakes, admin):
        user = fakes.accounts.add("sara", full_name_ar="سارة", department_id=7)  # not in setup

        result = update(fakes, admin, user.id, department_id=7, phone="0911")

        assert (result.department_id, result.phone) == (7, "0911")

    def test_remove_the_department(self, fakes, admin, endo):
        user = fakes.accounts.add("sara", full_name_ar="سارة", department_id=endo.id)

        assert update(fakes, admin, user.id, department_id=None).department_id is None


@pytest.mark.django_db
class TestUserScreens:
    @pytest.fixture
    def admin_client(self, dashboard):
        return dashboard("super_admin", username="admin")

    def test_create_a_user_in_a_department(self, admin_client):
        endo = Department.objects.create(name_ar="اللبية", name_en="Endodontics")
        Department.objects.create(name_ar="قديم", name_en="Old", is_active=False)

        form = admin_client.get("/dashboard/accounts/user/add/").context["adminform"].form
        assert [label for _value, label in form.fields["department"].choices] == [
            "—",
            "Endodontics",
        ]

        response = admin_client.post(
            "/dashboard/accounts/user/add/",
            {
                "username": "sara",
                "full_name_ar": "سارة",
                "roles": ["supervisor"],
                "department": endo.pk,
                "_save": "1",
            },
        )

        assert response.status_code == 200  # the temporary password page
        assert User.objects.get(username="sara").department_id == endo.pk

    def test_change_the_department_and_list_it(self, admin_client, make_user):
        endo = Department.objects.create(name_ar="اللبية", name_en="Endodontics")
        user = make_user("sara", "supervisor", full_name_ar="سارة")

        response = admin_client.post(
            f"/dashboard/accounts/user/{user.pk}/change/",
            {"full_name_ar": "سارة", "roles": ["supervisor"], "department": endo.pk, "_save": "1"},
        )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.department_id == endo.pk
        listed = admin_client.get(f"/dashboard/accounts/user/?department__id__exact={endo.pk}")
        assert [u.username for u in listed.context["cl"].result_list] == ["sara"]

    def test_an_unknown_department_shows_on_its_field(self, admin_client, make_user):
        user = make_user("sara", "supervisor", full_name_ar="سارة")

        response = admin_client.post(
            f"/dashboard/accounts/user/{user.pk}/change/",
            {"full_name_ar": "سارة", "roles": ["supervisor"], "department": 999, "_save": "1"},
        )

        assert "department" in response.context["adminform"].form.errors
