"""User administration services (DB-02): CreateUser, AssignRoles, ResetPassword,
UnlockAccount. Only the system administrator, acting in that role, may use them."""

from datetime import timedelta

import pytest

from apps.accounts.application.services import (
    AssignRoles,
    AssignRolesCommand,
    CreateUser,
    CreateUserCommand,
    ResetPassword,
    UnlockAccount,
)
from apps.core.application.dtos import Actor
from apps.core.domain.errors import AccessDeniedError, DomainError, NotFoundError


@pytest.fixture
def admin(fakes) -> Actor:
    account = fakes.accounts.add("admin", roles=("super_admin",))
    return Actor(account.id, "super_admin")


def create(f, actor, **values):
    values = {"username": "Sara.Ali", "full_name_ar": "سارة علي", "roles": ["student"], **values}
    return CreateUser(f.accounts, f.roles, f.hasher, f.passwords, f.audit, f.uow).execute(
        actor, CreateUserCommand(**values)
    )


def assign(f, actor, user_id, roles):
    return AssignRoles(f.accounts, f.roles, f.audit, f.uow).execute(
        actor, AssignRolesCommand(user_id, roles)
    )


def reset(f, actor, user_id):
    return ResetPassword(f.accounts, f.hasher, f.passwords, f.tokens, f.audit, f.uow).execute(
        actor, user_id
    )


def unlock(f, actor, user_id):
    return UnlockAccount(f.accounts, f.clock, f.audit, f.uow).execute(actor, user_id)


def not_admins(fakes):
    """A management user; and an administrator who is acting in another role now."""
    manager = fakes.accounts.add("manager", roles=("management",))
    two_roles = fakes.accounts.add("both", roles=("super_admin", "supervisor"))
    pretender = fakes.accounts.add("pretender", roles=("supervisor",))
    return [
        Actor(manager.id, "management"),
        Actor(two_roles.id, "supervisor"),
        Actor(pretender.id, "super_admin"),  # claims a role they do not hold
    ]


class TestCreateUser:
    def test_creates_the_user_with_a_temporary_password(self, fakes, admin):
        result = create(fakes, admin, full_name_en="Sara Ali", university_id=" 2026001 ")

        assert result.temporary_password == "Temp-Pass-4821"
        assert result.user.username == "sara.ali"
        assert result.user.roles == ("student",)
        assert result.user.university_id == "2026001"
        assert result.user.must_change_password is True
        stored = fakes.accounts.stored(result.user.id)
        assert stored.password_hash == "hashed:Temp-Pass-4821"

    def test_audits_the_creation(self, fakes, admin):
        result = create(fakes, admin)

        entry = fakes.audit.entries[0]
        assert (entry.action, entry.model, entry.object_id) == (
            "create",
            "accounts.User",
            str(result.user.id),
        )
        assert entry.changes["roles"] == {"old": None, "new": ["student"]}
        assert "Temp-Pass-4821" not in str(entry.changes)

    def test_several_roles(self, fakes, admin):
        result = create(fakes, admin, roles=["supervisor", "student"])

        assert result.user.roles == ("student", "supervisor")

    @pytest.mark.parametrize("make_actor", range(3))
    def test_only_the_system_administrator(self, fakes, make_actor):
        actor = not_admins(fakes)[make_actor]

        with pytest.raises(AccessDeniedError):
            create(fakes, actor)

    def test_username_taken_even_by_a_deactivated_user(self, fakes, admin):
        fakes.accounts.add("sara.ali", is_active=False)

        with pytest.raises(DomainError) as error:
            create(fakes, admin)

        assert error.value.code == "username_taken"

    def test_university_id_taken(self, fakes, admin):
        fakes.accounts.add("other", university_id="2026001")

        with pytest.raises(DomainError, match="university_id_taken"):
            create(fakes, admin, university_id="2026001")

    @pytest.mark.parametrize(
        ("values", "code"),
        [
            ({"roles": []}, "role_required"),
            ({"roles": ["dean"]}, "unknown_role"),
            ({"username": "bad name"}, "username_invalid"),
            ({"full_name_ar": " "}, "full_name_required"),
        ],
    )
    def test_guards(self, fakes, admin, values, code):
        with pytest.raises(DomainError) as error:
            create(fakes, admin, **values)

        assert error.value.code == code
        assert fakes.audit.entries == []

    def test_a_role_missing_from_the_role_table_is_unknown(self, fakes, admin):
        fakes.roles.codes = frozenset({"super_admin", "student"})

        with pytest.raises(DomainError, match="unknown_role"):
            create(fakes, admin, roles=["technician"])


class TestAssignRoles:
    def test_replaces_the_roles_and_audits(self, fakes, admin):
        user = fakes.accounts.add("sara", roles=("student",))

        result = assign(fakes, admin, user.id, ["supervisor", "student"])

        assert result.roles == ("student", "supervisor")
        assert fakes.audit.entries[0].changes == {
            "roles": {"old": ["student"], "new": ["student", "supervisor"]}
        }

    def test_the_administrator_keeps_their_own_admin_role(self, fakes, admin):
        with pytest.raises(DomainError) as error:
            assign(fakes, admin, admin.user_id, ["supervisor"])

        assert error.value.code == "own_admin_role"

    def test_needs_at_least_one_known_role(self, fakes, admin):
        user = fakes.accounts.add("sara")

        with pytest.raises(DomainError, match="role_required"):
            assign(fakes, admin, user.id, [])
        with pytest.raises(DomainError, match="unknown_role"):
            assign(fakes, admin, user.id, ["dean"])

    def test_unknown_or_deactivated_user_is_not_found(self, fakes, admin):
        user = fakes.accounts.add("sara", is_active=False)

        with pytest.raises(NotFoundError):
            assign(fakes, admin, user.id, ["student"])
        with pytest.raises(NotFoundError):
            assign(fakes, admin, 999, ["student"])

    @pytest.mark.parametrize("make_actor", range(3))
    def test_only_the_system_administrator(self, fakes, make_actor):
        user = fakes.accounts.add("sara")
        actor = not_admins(fakes)[make_actor]

        with pytest.raises(AccessDeniedError):
            assign(fakes, actor, user.id, ["supervisor"])


class TestResetPassword:
    def test_gives_a_new_temporary_password_and_revokes_tokens(self, fakes, admin):
        user = fakes.accounts.add(
            "sara", failed_logins=5, locked_until=fakes.clock.now() + timedelta(minutes=5)
        )
        fakes.tokens.issue(user.id)

        result = reset(fakes, admin, user.id)

        assert result.temporary_password == "Temp-Pass-4821"
        stored = fakes.accounts.stored(user.id)
        assert stored.password_hash == "hashed:Temp-Pass-4821"
        assert stored.must_change_password is True
        assert (stored.failed_logins, stored.locked_until) == (0, None)
        assert fakes.tokens.open_tokens(user.id) == set()
        assert fakes.audit.actions() == ["password_reset"]

    def test_unknown_user(self, fakes, admin):
        with pytest.raises(NotFoundError):
            reset(fakes, admin, 999)

    @pytest.mark.parametrize("make_actor", range(3))
    def test_only_the_system_administrator(self, fakes, make_actor):
        user = fakes.accounts.add("sara")
        actor = not_admins(fakes)[make_actor]

        with pytest.raises(AccessDeniedError):
            reset(fakes, actor, user.id)


class TestUnlockAccount:
    def test_unlocks_and_audits(self, fakes, admin):
        until = fakes.clock.now() + timedelta(minutes=10)
        user = fakes.accounts.add("sara", failed_logins=5, locked_until=until)

        result = unlock(fakes, admin, user.id)

        assert result.locked_until is None
        assert fakes.accounts.stored(user.id).failed_logins == 0
        assert fakes.audit.entries[0].action == "unlock"
        assert fakes.audit.entries[0].changes == {
            "locked_until": {"old": until.isoformat(), "new": None}
        }

    def test_an_account_that_is_not_locked(self, fakes, admin):
        user = fakes.accounts.add(
            "sara", failed_logins=5, locked_until=fakes.clock.now() - timedelta(seconds=1)
        )

        with pytest.raises(DomainError) as error:
            unlock(fakes, admin, user.id)

        assert error.value.code == "account_not_locked"

    def test_unknown_user(self, fakes, admin):
        with pytest.raises(NotFoundError):
            unlock(fakes, admin, 999)

    @pytest.mark.parametrize("make_actor", range(3))
    def test_only_the_system_administrator(self, fakes, make_actor):
        user = fakes.accounts.add(
            "sara", failed_logins=5, locked_until=fakes.clock.now() + timedelta(minutes=10)
        )
        actor = not_admins(fakes)[make_actor]

        with pytest.raises(AccessDeniedError):
            unlock(fakes, actor, user.id)
