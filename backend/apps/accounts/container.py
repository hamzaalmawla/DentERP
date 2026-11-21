"""Builds the accounts services with their real adapters (design section 5)."""

from apps.core import container as core

from .application.queries import GetAuthContext, GetProfile
from .application.services import (
    AssignRoles,
    ChangePassword,
    CreateDemoUsers,
    CreateUser,
    DeactivateUser,
    Login,
    Logout,
    RefreshToken,
    RegisterDevice,
    ResetPassword,
    UnlockAccount,
    UpdateUser,
    VerifyCredentials,
)
from .infrastructure.passwords import (
    DjangoPasswordHasher,
    DjangoPasswordPolicy,
    SecretsPasswordGenerator,
)
from .infrastructure.repositories import (
    OrmAccountRepository,
    OrmAuthContextReader,
    OrmDeviceTokenRepository,
    OrmRoleRepository,
)
from .infrastructure.tokens import SimpleJwtTokenIssuer


def login() -> Login:
    return Login(
        OrmAccountRepository(),
        DjangoPasswordHasher(),
        SimpleJwtTokenIssuer(),
        core.clock(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def verify_credentials() -> VerifyCredentials:
    return VerifyCredentials(
        OrmAccountRepository(),
        DjangoPasswordHasher(),
        core.clock(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def refresh_token() -> RefreshToken:
    return RefreshToken(OrmAccountRepository(), SimpleJwtTokenIssuer(), core.unit_of_work())


def logout() -> Logout:
    return Logout(SimpleJwtTokenIssuer(), core.audit_logger(), core.unit_of_work())


def change_password() -> ChangePassword:
    return ChangePassword(
        OrmAccountRepository(),
        DjangoPasswordHasher(),
        DjangoPasswordPolicy(),
        SimpleJwtTokenIssuer(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def register_device() -> RegisterDevice:
    return RegisterDevice(
        OrmAccountRepository(), OrmDeviceTokenRepository(), core.clock(), core.unit_of_work()
    )


def create_user() -> CreateUser:
    return CreateUser(
        OrmAccountRepository(),
        OrmRoleRepository(),
        DjangoPasswordHasher(),
        SecretsPasswordGenerator(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def assign_roles() -> AssignRoles:
    return AssignRoles(
        OrmAccountRepository(), OrmRoleRepository(), core.audit_logger(), core.unit_of_work()
    )


def reset_password() -> ResetPassword:
    return ResetPassword(
        OrmAccountRepository(),
        DjangoPasswordHasher(),
        SecretsPasswordGenerator(),
        SimpleJwtTokenIssuer(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def unlock_account() -> UnlockAccount:
    return UnlockAccount(
        OrmAccountRepository(), core.clock(), core.audit_logger(), core.unit_of_work()
    )


def update_user() -> UpdateUser:
    return UpdateUser(OrmAccountRepository(), core.audit_logger(), core.unit_of_work())


def deactivate_user() -> DeactivateUser:
    return DeactivateUser(
        OrmAccountRepository(), SimpleJwtTokenIssuer(), core.audit_logger(), core.unit_of_work()
    )


def create_demo_users() -> CreateDemoUsers:
    return CreateDemoUsers(
        OrmAccountRepository(),
        OrmRoleRepository(),
        DjangoPasswordHasher(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def get_profile() -> GetProfile:
    return GetProfile(OrmAccountRepository())


def get_auth_context() -> GetAuthContext:
    return GetAuthContext(OrmAuthContextReader())
