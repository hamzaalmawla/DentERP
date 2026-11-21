"""Accounts use cases (design sections 5 and 8): one class per use case.

Each service gets its ports through the constructor (``container.py`` builds them) and returns
DTOs. Every login, failed login and password change is written to the audit log (SYS-04).
"""

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from apps.accounts.domain.accounts import normalize_username
from apps.accounts.domain.devices import validate_device
from apps.accounts.domain.errors import (
    AccountLockedError,
    AccountNotLockedError,
    DashboardNotAllowedError,
    InvalidCredentialsError,
    InvalidTokenError,
    NoRoleError,
    OwnAccountError,
    OwnAdminRoleError,
    PasswordInvalidError,
    PasswordUnchangedError,
    RoleRequiredError,
    UniversityIdTakenError,
    UnknownRoleError,
    UserManagementDeniedError,
    UsernameTakenError,
    WrongPasswordError,
)
from apps.accounts.domain.roles import DASHBOARD_ROLES, RoleCode
from apps.accounts.domain.users import validate_full_name, validate_username
from apps.core.application.dtos import Actor
from apps.core.application.ports import AuditLogger, Clock, UnitOfWork
from apps.core.domain.audit import AuditAction, diff
from apps.core.domain.errors import DomainError, NotFoundError

from .dtos import (
    DeviceDTO,
    LoginResult,
    NewAccount,
    TemporaryPasswordResult,
    TokenPair,
    UserDetails,
    UserDTO,
    VerifiedUser,
)
from .ports import (
    AccountRepository,
    DeviceTokenRepository,
    PasswordHasher,
    PasswordPolicy,
    RoleRepository,
    TemporaryPasswordGenerator,
    TokenIssuer,
)

USER_MODEL = "accounts.User"

# Audit actions of this module that core's AuditAction does not name.
PASSWORD_RESET = "password_reset"
UNLOCK = "unlock"


def _found[T](item: T | None) -> T:
    if item is None:
        raise NotFoundError()
    return item


def _ensure_user_manager(actor: Actor, accounts: AccountRepository) -> None:
    """Only the system administrator manages users (DB-02). The role must be the one the
    actor is using now and one they still hold."""
    if actor.role != RoleCode.SUPER_ADMIN or RoleCode.SUPER_ADMIN not in accounts.roles_of(
        actor.user_id
    ):
        raise UserManagementDeniedError()


def _valid_roles(roles: Iterable[str], known: frozenset[str]) -> frozenset[str]:
    wanted = frozenset(roles)
    if not wanted:
        raise RoleRequiredError()
    unknown = wanted - known
    if unknown:
        raise UnknownRoleError(sorted(unknown))
    return wanted


# --- Login and tokens (SYS-01, ST-01) ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerifyCredentialsCommand:
    username: str
    password: str
    # The dashboard is open only to DASHBOARD_ROLES (design section 8).
    for_dashboard: bool = False


class VerifyCredentials:
    """Checks a username and password with the login rules (SYS-01), for the API login and
    the dashboard login alike.

    Five failed logins in a row lock the account for 15 minutes; a locked account is refused
    even with the right password; a user without a role is refused. Every login and failed
    login is audited. A refused login still records the failure, so the error is raised after
    the unit of work has committed.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        hasher: PasswordHasher,
        clock: Clock,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._hasher = hasher
        self._clock = clock
        self._audit = audit
        self._uow = uow

    def execute(self, command: VerifyCredentialsCommand) -> VerifiedUser:
        username = normalize_username(command.username)
        now = self._clock.now()
        error: DomainError | None = None
        result: VerifiedUser | None = None
        with self._uow:
            account = self._accounts.get_by_username(username, for_update=True)
            if account is None:
                self._hasher.spend_time(command.password)
                self._failed(None, username, "unknown_user")
                error = InvalidCredentialsError()
            elif account.is_locked(now):
                self._failed(account.id, username, "locked")
                error = AccountLockedError(account.locked_until)
            elif not self._hasher.verify(command.password, account.password_hash):
                account = account.after_failed_login(now)
                self._accounts.save(account)
                self._failed(account.id, username, "wrong_password")
                error = (
                    AccountLockedError(account.locked_until)
                    if account.is_locked(now)
                    else InvalidCredentialsError()
                )
            elif not (roles := self._accounts.roles_of(account.id)):
                self._failed(account.id, username, "no_role")
                error = NoRoleError()
            elif command.for_dashboard and not roles & DASHBOARD_ROLES:
                self._failed(account.id, username, "dashboard_not_allowed")
                error = DashboardNotAllowedError()
            else:
                account = account.after_successful_login(now)
                self._accounts.save(account)
                self._audit.log(
                    AuditAction.LOGIN, model=USER_MODEL, object_id=account.id, user_id=account.id
                )
                result = VerifiedUser(
                    user_id=account.id,
                    roles=roles,
                    must_change_password=account.must_change_password,
                )
        if error is not None:
            raise error
        assert result is not None
        return result

    def _failed(self, user_id: int | None, username: str, reason: str) -> None:
        self._audit.log(
            AuditAction.LOGIN_FAILED,
            model=USER_MODEL,
            object_id=user_id,
            changes={"username": username, "reason": reason},
            user_id=user_id,
        )


@dataclass(frozen=True, slots=True)
class LoginCommand:
    username: str
    password: str


class Login:
    """Username and password → tokens and roles (the API login). The credentials are checked
    by ``VerifyCredentials``, the same rules the dashboard login uses."""

    def __init__(
        self,
        accounts: AccountRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        clock: Clock,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._verify = VerifyCredentials(accounts, hasher, clock, audit, uow)
        self._tokens = tokens
        self._uow = uow

    def execute(self, command: LoginCommand) -> LoginResult:
        user = self._verify.execute(VerifyCredentialsCommand(command.username, command.password))
        with self._uow:
            tokens = self._tokens.issue(user.user_id)
        return LoginResult(
            access=tokens.access,
            refresh=tokens.refresh,
            must_change_password=user.must_change_password,
            roles=tuple(sorted(user.roles)),
        )


class RefreshToken:
    """A refresh token → a new pair. The old refresh token is revoked (rotation)."""

    def __init__(self, accounts: AccountRepository, tokens: TokenIssuer, uow: UnitOfWork) -> None:
        self._accounts = accounts
        self._tokens = tokens
        self._uow = uow

    def execute(self, refresh: str) -> TokenPair:
        with self._uow:
            user_id = self._tokens.user_of(refresh)
            if self._accounts.get(user_id) is None:  # deactivated since the token was issued
                raise InvalidTokenError()
            return self._tokens.rotate(refresh)


class Logout:
    """Revokes the refresh token, so it cannot get new access tokens."""

    def __init__(self, tokens: TokenIssuer, audit: AuditLogger, uow: UnitOfWork) -> None:
        self._tokens = tokens
        self._audit = audit
        self._uow = uow

    def execute(self, refresh: str) -> None:
        with self._uow:
            user_id = self._tokens.revoke(refresh)
            self._audit.log(
                AuditAction.LOGOUT, model=USER_MODEL, object_id=user_id, user_id=user_id
            )


# --- The user's own account (ST-01) -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    user_id: int
    current_password: str
    new_password: str


class ChangePassword:
    """The user changes their own password; this also lifts the first-login gate.

    Every token issued before is revoked and a new pair is returned, so other phones that used
    the old password are logged out.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        hasher: PasswordHasher,
        policy: PasswordPolicy,
        tokens: TokenIssuer,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._hasher = hasher
        self._policy = policy
        self._tokens = tokens
        self._audit = audit
        self._uow = uow

    def execute(self, command: ChangePasswordCommand) -> TokenPair:
        with self._uow:
            account = _found(self._accounts.get(command.user_id, for_update=True))
            if not self._hasher.verify(command.current_password, account.password_hash):
                raise WrongPasswordError()
            if command.new_password == command.current_password:
                raise PasswordUnchangedError()
            problems = self._policy.problems(command.new_password, account)
            if problems:
                raise PasswordInvalidError(problems)
            self._accounts.save(
                account.with_password(self._hasher.hash(command.new_password), temporary=False)
            )
            self._tokens.revoke_all(account.id)
            tokens = self._tokens.issue(account.id)
            self._audit.log(
                AuditAction.PASSWORD_CHANGE,
                model=USER_MODEL,
                object_id=account.id,
                changes=diff(
                    {"must_change_password": account.must_change_password},
                    {"must_change_password": False},
                ),
                user_id=account.id,
            )
        return tokens


@dataclass(frozen=True, slots=True)
class RegisterDeviceCommand:
    user_id: int
    platform: str
    token: str


class RegisterDevice:
    """Stores the phone's push token for the user (SYS-03)."""

    def __init__(
        self,
        accounts: AccountRepository,
        devices: DeviceTokenRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._devices = devices
        self._clock = clock
        self._uow = uow

    def execute(self, command: RegisterDeviceCommand) -> DeviceDTO:
        platform, token = validate_device(command.platform, command.token)
        with self._uow:
            _found(self._accounts.get(command.user_id))
            return self._devices.register(command.user_id, platform, token, self._clock.now())


# --- User administration (DB-02), used by the dashboard ------------------------------


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    username: str
    full_name_ar: str
    roles: Sequence[str]
    full_name_en: str = ""
    phone: str = ""
    university_id: str = ""


class CreateUser:
    """Creates a user with their roles and a temporary password, which must be changed at the
    first login."""

    def __init__(
        self,
        accounts: AccountRepository,
        roles: RoleRepository,
        hasher: PasswordHasher,
        passwords: TemporaryPasswordGenerator,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._roles = roles
        self._hasher = hasher
        self._passwords = passwords
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, command: CreateUserCommand) -> TemporaryPasswordResult:
        _ensure_user_manager(actor, self._accounts)
        username = validate_username(normalize_username(command.username))
        full_name_ar = validate_full_name(command.full_name_ar)
        roles = _valid_roles(command.roles, self._roles.active_codes())
        university_id = command.university_id.strip() or None
        with self._uow:
            if self._accounts.username_exists(username):
                raise UsernameTakenError(username)
            if university_id and self._accounts.university_id_exists(university_id):
                raise UniversityIdTakenError(university_id)
            temporary_password = self._passwords.generate()
            values = {
                "username": username,
                "full_name_ar": full_name_ar,
                "full_name_en": command.full_name_en.strip(),
                "phone": command.phone.strip(),
                "university_id": university_id,
            }
            user_id = self._accounts.create(
                NewAccount(
                    **values,
                    password_hash=self._hasher.hash(temporary_password),
                    must_change_password=True,
                    roles=roles,
                )
            )
            self._audit.log(
                AuditAction.CREATE,
                model=USER_MODEL,
                object_id=user_id,
                changes=diff({}, {**values, "roles": sorted(roles)}),
            )
            user = _found(self._accounts.to_dto(user_id))
        return TemporaryPasswordResult(user=user, temporary_password=temporary_password)


@dataclass(frozen=True, slots=True)
class AssignRolesCommand:
    user_id: int
    roles: Sequence[str]


class AssignRoles:
    """Replaces the user's roles. The administrator cannot remove their own admin role, so the
    system always keeps one administrator who can fix mistakes."""

    def __init__(
        self,
        accounts: AccountRepository,
        roles: RoleRepository,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._roles = roles
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, command: AssignRolesCommand) -> UserDTO:
        _ensure_user_manager(actor, self._accounts)
        roles = _valid_roles(command.roles, self._roles.active_codes())
        if command.user_id == actor.user_id and RoleCode.SUPER_ADMIN not in roles:
            raise OwnAdminRoleError()
        with self._uow:
            _found(self._accounts.get(command.user_id, for_update=True))
            before = self._accounts.roles_of(command.user_id)
            self._accounts.set_roles(command.user_id, roles)
            self._audit.log(
                AuditAction.UPDATE,
                model=USER_MODEL,
                object_id=command.user_id,
                changes=diff({"roles": sorted(before)}, {"roles": sorted(roles)}),
            )
            return _found(self._accounts.to_dto(command.user_id))


class ResetPassword:
    """Gives the user a new temporary password: the account is unlocked, every token is revoked
    and the user must change the password at the next login."""

    def __init__(
        self,
        accounts: AccountRepository,
        hasher: PasswordHasher,
        passwords: TemporaryPasswordGenerator,
        tokens: TokenIssuer,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._hasher = hasher
        self._passwords = passwords
        self._tokens = tokens
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, user_id: int) -> TemporaryPasswordResult:
        _ensure_user_manager(actor, self._accounts)
        with self._uow:
            account = _found(self._accounts.get(user_id, for_update=True))
            temporary_password = self._passwords.generate()
            self._accounts.save(
                account.with_password(
                    self._hasher.hash(temporary_password), temporary=True
                ).unlocked()
            )
            self._tokens.revoke_all(user_id)
            self._audit.log(PASSWORD_RESET, model=USER_MODEL, object_id=user_id)
            user = _found(self._accounts.to_dto(user_id))
        return TemporaryPasswordResult(user=user, temporary_password=temporary_password)


class UnlockAccount:
    """Lifts a lockout before its 15 minutes run out (design section 8)."""

    def __init__(
        self, accounts: AccountRepository, clock: Clock, audit: AuditLogger, uow: UnitOfWork
    ) -> None:
        self._accounts = accounts
        self._clock = clock
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, user_id: int) -> UserDTO:
        _ensure_user_manager(actor, self._accounts)
        with self._uow:
            account = _found(self._accounts.get(user_id, for_update=True))
            if not account.is_locked(self._clock.now()):
                raise AccountNotLockedError()
            self._accounts.save(account.unlocked())
            self._audit.log(
                UNLOCK,
                model=USER_MODEL,
                object_id=user_id,
                changes=diff(
                    {"locked_until": account.locked_until.isoformat()}, {"locked_until": None}
                ),
            )
            return _found(self._accounts.to_dto(user_id))


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    user_id: int
    full_name_ar: str
    full_name_en: str = ""
    phone: str = ""
    university_id: str = ""


class UpdateUser:
    """Changes a user's names, phone and university ID (DB-02). The username never changes;
    roles change through ``AssignRoles``."""

    def __init__(self, accounts: AccountRepository, audit: AuditLogger, uow: UnitOfWork) -> None:
        self._accounts = accounts
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, command: UpdateUserCommand) -> UserDTO:
        _ensure_user_manager(actor, self._accounts)
        details = UserDetails(
            full_name_ar=validate_full_name(command.full_name_ar),
            full_name_en=command.full_name_en.strip(),
            phone=command.phone.strip(),
            university_id=command.university_id.strip() or None,
        )
        with self._uow:
            _found(self._accounts.get(command.user_id, for_update=True))
            before = _found(self._accounts.details_of(command.user_id))
            if details.university_id and self._accounts.university_id_exists(
                details.university_id, exclude_user_id=command.user_id
            ):
                raise UniversityIdTakenError(details.university_id)
            changes = diff(asdict(before), asdict(details))
            if changes:
                self._accounts.update_details(command.user_id, details)
                self._audit.log(
                    AuditAction.UPDATE,
                    model=USER_MODEL,
                    object_id=command.user_id,
                    changes=changes,
                )
            return _found(self._accounts.to_dto(command.user_id))


class DeactivateUser:
    """Deactivates a user (DB-02): they can no longer log in, every token they hold is revoked,
    and their records stay (users are never deleted, SYS-10). The username is never reused.
    The administrator cannot deactivate their own account."""

    def __init__(
        self,
        accounts: AccountRepository,
        tokens: TokenIssuer,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._tokens = tokens
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, user_id: int) -> None:
        _ensure_user_manager(actor, self._accounts)
        if user_id == actor.user_id:
            raise OwnAccountError()
        with self._uow:
            _found(self._accounts.get(user_id, for_update=True))
            self._accounts.deactivate(user_id)
            self._tokens.revoke_all(user_id)
            self._audit.log(
                AuditAction.DEACTIVATE,
                model=USER_MODEL,
                object_id=user_id,
                changes=diff({"is_active": True}, {"is_active": False}),
            )


# --- Development data -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DemoUser:
    username: str
    role: str


DEMO_USERNAME_PREFIX = "demo_"


class CreateDemoUsers:
    """One user per role, all with the same known password, for development and demos.
    Users that already exist are left as they are, so it is safe to run again."""

    def __init__(
        self,
        accounts: AccountRepository,
        roles: RoleRepository,
        hasher: PasswordHasher,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._accounts = accounts
        self._roles = roles
        self._hasher = hasher
        self._audit = audit
        self._uow = uow

    def execute(self, password: str) -> list[DemoUser]:
        created: list[DemoUser] = []
        known = self._roles.active_codes()
        with self._uow:
            password_hash = self._hasher.hash(password)
            for role in RoleCode:
                username = f"{DEMO_USERNAME_PREFIX}{role}"
                if role not in known or self._accounts.username_exists(username):
                    continue
                user_id = self._accounts.create(
                    NewAccount(
                        username=username,
                        full_name_ar=f"مستخدم تجريبي ({role})",
                        full_name_en=f"Demo {role.replace('_', ' ')}",
                        phone="",
                        university_id=None,
                        password_hash=password_hash,
                        must_change_password=False,
                        roles=frozenset({role}),
                    )
                )
                self._audit.log(
                    AuditAction.CREATE,
                    model=USER_MODEL,
                    object_id=user_id,
                    changes=diff({}, {"username": username, "roles": [str(role)]}),
                )
                created.append(DemoUser(username=username, role=str(role)))
        return created
