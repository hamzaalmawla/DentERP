"""Ports of the accounts module. Adapters: ``infrastructure/``; fakes: ``testing/``."""

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.accounts.domain.accounts import Account
from apps.setup.application.facade import SetupFacade

from .dtos import AuthContext, DeviceDTO, NewAccount, TokenPair, UserDetails, UserDTO

# The setup module's facade: a user's department (DB-02) must be an active department.
__all__ = [
    "AccountRepository",
    "AuthContextReader",
    "DeviceTokenRepository",
    "PasswordHasher",
    "PasswordPolicy",
    "RoleRepository",
    "SetupFacade",
    "TemporaryPasswordGenerator",
    "TokenIssuer",
]


@runtime_checkable
class AccountRepository(Protocol):
    """The user aggregate: the account and its roles. Only active users are found."""

    def get(self, user_id: int, *, for_update: bool = False) -> Account | None: ...

    def get_by_username(self, username: str, *, for_update: bool = False) -> Account | None:
        """``username`` is already normalised (``domain.accounts.normalize_username``)."""
        ...

    def save(self, account: Account) -> None:
        """Store the login state and password of an existing account."""
        ...

    def create(self, account: NewAccount) -> int:
        """Create the account with its roles; returns its id."""
        ...

    def username_exists(self, username: str) -> bool:
        """Also true for deactivated users: a username is never reused."""
        ...

    def university_id_exists(
        self, university_id: str, *, exclude_user_id: int | None = None
    ) -> bool:
        """Also true for deactivated users. ``exclude_user_id`` leaves that user out."""
        ...

    def details_of(self, user_id: int) -> UserDetails | None: ...

    def update_details(self, user_id: int, details: UserDetails) -> None: ...

    def deactivate(self, user_id: int) -> None:
        """Hide the user: they can no longer log in and are no longer found. Nothing is
        deleted (SYS-10)."""
        ...

    def roles_of(self, user_id: int) -> frozenset[str]: ...

    def set_roles(self, user_id: int, roles: Iterable[str]) -> None: ...

    def to_dto(self, user_id: int) -> UserDTO | None: ...


@runtime_checkable
class RoleRepository(Protocol):
    def active_codes(self) -> frozenset[str]:
        """The codes of the roles that exist and are active in the ``Role`` table."""
        ...


@runtime_checkable
class AuthContextReader(Protocol):
    """Read side used on every request: roles and the password gate of one user."""

    def auth_context(self, user_id: int) -> AuthContext | None: ...


@runtime_checkable
class DeviceTokenRepository(Protocol):
    def register(self, user_id: int, platform: str, token: str, seen_at: datetime) -> DeviceDTO:
        """Store the push token for the user. A token is unique: one registered by another
        user (the phone changed hands) moves to this user."""
        ...


@runtime_checkable
class PasswordHasher(Protocol):
    def hash(self, raw_password: str) -> str: ...

    def verify(self, raw_password: str, password_hash: str) -> bool: ...

    def spend_time(self, raw_password: str) -> None:
        """Hash once and throw the result away, so a login for an unknown user takes as long
        as a login for a known one."""
        ...


@runtime_checkable
class PasswordPolicy(Protocol):
    def problems(self, raw_password: str, account: Account) -> Sequence[str]:
        """Messages for each password rule the password breaks; empty when it is acceptable."""
        ...


@runtime_checkable
class TemporaryPasswordGenerator(Protocol):
    def generate(self) -> str: ...


@runtime_checkable
class TokenIssuer(Protocol):
    """JWT tokens (design section 8). Invalid, expired or revoked tokens raise
    ``InvalidTokenError``."""

    def issue(self, user_id: int) -> TokenPair: ...

    def user_of(self, refresh: str) -> int:
        """The user a valid refresh token belongs to."""
        ...

    def rotate(self, refresh: str) -> TokenPair:
        """A new pair; the old refresh token is revoked and cannot be used again."""
        ...

    def revoke(self, refresh: str) -> int:
        """Revoke a refresh token; returns its user."""
        ...

    def revoke_all(self, user_id: int) -> None:
        """Revoke every refresh token of the user."""
        ...
