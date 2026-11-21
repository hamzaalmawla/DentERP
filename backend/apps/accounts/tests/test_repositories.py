"""ORM adapters against PostgreSQL."""

from dataclasses import replace
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.application.dtos import NewAccount
from apps.accounts.infrastructure.repositories import (
    OrmAccountRepository,
    OrmAuthContextReader,
    OrmDeviceTokenRepository,
    OrmRoleRepository,
)
from apps.accounts.models import DeviceToken, Role, User, UserRole

pytestmark = pytest.mark.django_db


def new_account(**values) -> NewAccount:
    defaults = {
        "username": "sara",
        "full_name_ar": "سارة",
        "full_name_en": "Sara",
        "phone": "0999",
        "university_id": "2026001",
        "password_hash": "pbkdf2$hash",
        "must_change_password": True,
        "roles": frozenset({"student", "supervisor"}),
    }
    return NewAccount(**{**defaults, **values})


class TestAccountRepository:
    repo = OrmAccountRepository()

    def test_create_and_read(self):
        user_id = self.repo.create(new_account())

        account = self.repo.get(user_id)
        assert (account.username, account.password_hash) == ("sara", "pbkdf2$hash")
        assert account.must_change_password is True
        dto = self.repo.to_dto(user_id)
        assert dto.roles == ("student", "supervisor")
        assert (dto.phone, dto.university_id) == ("0999", "2026001")
        assert self.repo.get_by_username("sara").id == user_id

    def test_save_stores_the_login_state(self):
        user_id = self.repo.create(new_account())
        now = timezone.now()
        account = replace(
            self.repo.get(user_id),
            failed_logins=5,
            locked_until=now + timedelta(minutes=15),
            last_login=now,
            password_hash="new",
            must_change_password=False,
        )

        with transaction.atomic():
            self.repo.save(account)

        assert self.repo.get(user_id) == account

    def test_get_for_update_inside_a_transaction(self):
        user_id = self.repo.create(new_account())

        with transaction.atomic():
            assert self.repo.get(user_id, for_update=True).id == user_id
            assert self.repo.get_by_username("sara", for_update=True).id == user_id

    def test_deactivated_users_are_not_found_but_their_username_stays_taken(self):
        user_id = self.repo.create(new_account())
        User.objects.get(pk=user_id).deactivate()

        assert self.repo.get(user_id) is None
        assert self.repo.get_by_username("sara") is None
        assert self.repo.to_dto(user_id) is None
        assert self.repo.username_exists("sara")
        assert self.repo.university_id_exists("2026001")
        assert not self.repo.username_exists("omar")

    def test_set_roles_deactivates_and_reactivates_rows(self):
        user_id = self.repo.create(new_account())

        self.repo.set_roles(user_id, {"student"})
        assert self.repo.roles_of(user_id) == {"student"}
        self.repo.set_roles(user_id, {"student", "supervisor", "technician"})

        assert self.repo.roles_of(user_id) == {"student", "supervisor", "technician"}
        assert UserRole.all_objects.filter(user_id=user_id).count() == 3  # no duplicate rows

    def test_a_deactivated_role_is_not_held(self):
        user_id = self.repo.create(new_account())
        Role.objects.get(code="supervisor").deactivate()

        assert self.repo.roles_of(user_id) == {"student"}
        assert self.repo.to_dto(user_id).roles == ("student",)

    def test_university_id_is_unique_when_set(self):
        self.repo.create(new_account(university_id=None))
        self.repo.create(new_account(username="omar", university_id=None))

        self.repo.create(new_account(username="lina"))

        with pytest.raises(IntegrityError), transaction.atomic():
            self.repo.create(new_account(username="huda"))


class TestOtherRepositories:
    def test_roles_are_loaded_by_the_data_migration(self):
        assert OrmRoleRepository().active_codes() == {
            "super_admin",
            "management",
            "reception",
            "supervisor",
            "student",
            "technician",
        }
        assert Role.objects.get(code="student").name_ar == "طالب"

    def test_auth_context(self):
        user_id = OrmAccountRepository().create(new_account())

        context = OrmAuthContextReader().auth_context(user_id)

        assert context.roles == {"student", "supervisor"}
        assert context.must_change_password is True
        assert OrmAuthContextReader().auth_context(999_999) is None

    def test_devices(self):
        repo = OrmDeviceTokenRepository()
        sara = OrmAccountRepository().create(new_account())
        omar = OrmAccountRepository().create(new_account(username="omar", university_id=None))
        now = timezone.now()

        with transaction.atomic():
            first = repo.register(sara, "android", "tok", now)
            DeviceToken.objects.get(pk=first.id).deactivate()  # e.g. FCM said it expired
            moved = repo.register(omar, "ios", "tok", now + timedelta(days=1))

        device = DeviceToken.objects.get(token="tok")
        assert moved.id == first.id
        assert (device.user_id, device.platform, device.is_active) == (omar, "ios", True)
        assert device.last_seen == now + timedelta(days=1)


class TestUserModel:
    def test_create_user_lowercases_and_hashes(self):
        user = User.objects.create_user(" Sara ", "Strong-Pass-2026", full_name_ar="سارة")

        assert user.username == "sara"
        assert user.check_password("Strong-Pass-2026")
        assert User.objects.get_by_natural_key("SARA") == user

    def test_create_superuser_holds_the_super_admin_role(self):
        user = User.objects.create_superuser("root", "Strong-Pass-2026", full_name_ar="المدير")

        assert user.is_superuser
        assert OrmAccountRepository().roles_of(user.pk) == {"super_admin"}

    def test_users_are_never_deleted(self):
        user = User.objects.create_user("sara", "x", full_name_ar="سارة")

        with pytest.raises(Exception, match="cannot be deleted"):
            user.delete()
        user.deactivate()
        assert not User.objects.filter(pk=user.pk).exists()
        assert User.all_objects.filter(pk=user.pk).exists()

    def test_inherits_the_base_model_fields(self):
        names = {field.name for field in User._meta.get_fields()}

        assert {"created_at", "created_by", "updated_at", "updated_by", "is_active"} <= names
        assert {"must_change_password", "failed_logins", "locked_until"} <= names
