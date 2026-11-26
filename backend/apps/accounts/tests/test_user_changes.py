"""UpdateUser and DeactivateUser (DB-02), with in-memory fakes. Only the system
administrator, acting in that role, may use them."""

import pytest

from apps.accounts.application.services import (
    DeactivateUser,
    UpdateUser,
    UpdateUserCommand,
)
from apps.accounts.tests.test_user_admin import not_admins
from apps.core.application.dtos import Actor
from apps.core.domain.errors import AccessDeniedError, DomainError, NotFoundError


@pytest.fixture
def admin(fakes) -> Actor:
    account = fakes.accounts.add("admin", roles=("super_admin",))
    return Actor(account.id, "super_admin")


def update(f, actor, user_id, **values):
    values = {"full_name_ar": "سارة علي", **values}
    return UpdateUser(f.accounts, f.setup, f.audit, f.uow).execute(
        actor, UpdateUserCommand(user_id=user_id, **values)
    )


def deactivate(f, actor, user_id):
    return DeactivateUser(f.accounts, f.tokens, f.audit, f.uow).execute(actor, user_id)


class TestUpdateUser:
    def test_changes_the_details_and_audits_the_diff(self, fakes, admin):
        user = fakes.accounts.add("sara", full_name_ar="سارة", phone="0911")

        result = update(
            fakes, admin, user.id, full_name_en=" Sara Ali ", phone="0911", university_id=" 77 "
        )

        assert (result.full_name_ar, result.full_name_en) == ("سارة علي", "Sara Ali")
        assert (result.phone, result.university_id, result.username) == ("0911", "77", "sara")
        entry = fakes.audit.entries[-1]
        assert (entry.action, entry.object_id) == ("update", str(user.id))
        assert entry.changes == {
            "full_name_ar": {"old": "سارة", "new": "سارة علي"},
            "full_name_en": {"old": "", "new": "Sara Ali"},
            "university_id": {"old": None, "new": "77"},
        }

    def test_nothing_changed_writes_no_audit_entry(self, fakes, admin):
        user = fakes.accounts.add("sara", full_name_ar="سارة علي")

        update(fakes, admin, user.id)

        assert fakes.audit.entries == []

    def test_keeping_your_own_university_id_is_allowed(self, fakes, admin):
        user = fakes.accounts.add("sara", university_id="77")

        assert update(fakes, admin, user.id, university_id="77").university_id == "77"

    def test_university_id_of_another_user(self, fakes, admin):
        fakes.accounts.add("other", university_id="77", is_active=False)
        user = fakes.accounts.add("sara")

        with pytest.raises(DomainError) as error:
            update(fakes, admin, user.id, university_id="77")

        assert error.value.code == "university_id_taken"

    def test_full_name_is_required(self, fakes, admin):
        user = fakes.accounts.add("sara")

        with pytest.raises(DomainError) as error:
            update(fakes, admin, user.id, full_name_ar="  ")

        assert error.value.code == "full_name_required"

    def test_unknown_or_deactivated_user_is_not_found(self, fakes, admin):
        gone = fakes.accounts.add("gone", is_active=False)

        for user_id in (gone.id, 999):
            with pytest.raises(NotFoundError):
                update(fakes, admin, user_id)

    @pytest.mark.parametrize("make_actor", range(3))
    def test_only_the_system_administrator(self, fakes, make_actor):
        user = fakes.accounts.add("sara")
        actor = not_admins(fakes)[make_actor]

        with pytest.raises(AccessDeniedError):
            update(fakes, actor, user.id)


class TestDeactivateUser:
    def test_deactivates_revokes_tokens_and_audits(self, fakes, admin):
        user = fakes.accounts.add("sara")
        fakes.tokens.issue(user.id)

        deactivate(fakes, admin, user.id)

        assert fakes.accounts.is_active(user.id) is False
        assert fakes.accounts.get(user.id) is None
        assert fakes.tokens.open_tokens(user.id) == set()
        entry = fakes.audit.entries[-1]
        assert (entry.action, entry.object_id) == ("deactivate", str(user.id))
        assert entry.changes == {"is_active": {"old": True, "new": False}}

    def test_the_username_stays_taken(self, fakes, admin):
        user = fakes.accounts.add("sara")

        deactivate(fakes, admin, user.id)

        assert fakes.accounts.username_exists("sara")

    def test_the_administrator_cannot_deactivate_themselves(self, fakes, admin):
        with pytest.raises(DomainError) as error:
            deactivate(fakes, admin, admin.user_id)

        assert error.value.code == "own_account"
        assert fakes.accounts.is_active(admin.user_id)

    def test_unknown_or_already_deactivated_user_is_not_found(self, fakes, admin):
        gone = fakes.accounts.add("gone", is_active=False)

        for user_id in (gone.id, 999):
            with pytest.raises(NotFoundError):
                deactivate(fakes, admin, user_id)

    @pytest.mark.parametrize("make_actor", range(3))
    def test_only_the_system_administrator(self, fakes, make_actor):
        user = fakes.accounts.add("sara")
        actor = not_admins(fakes)[make_actor]

        with pytest.raises(AccessDeniedError):
            deactivate(fakes, actor, user.id)

        assert fakes.accounts.is_active(user.id)
