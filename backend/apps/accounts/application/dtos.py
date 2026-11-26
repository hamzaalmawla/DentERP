"""What the accounts services return. Frozen dataclasses, never model instances."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TokenPair:
    access: str
    refresh: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    """``POST /auth/login/``: the tokens, the roles to choose from and the first-login gate."""

    access: str
    refresh: str
    must_change_password: bool
    roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VerifiedUser:
    """A user whose username and password were accepted (``VerifyCredentials``)."""

    user_id: int
    roles: frozenset[str]
    must_change_password: bool


@dataclass(frozen=True, slots=True)
class AuthContext:
    """What every authenticated request needs to know about its user (read once per request)."""

    user_id: int
    roles: frozenset[str]
    must_change_password: bool


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: int
    username: str
    full_name_ar: str
    full_name_en: str
    phone: str
    university_id: str | None
    roles: tuple[str, ...]
    must_change_password: bool
    locked_until: datetime | None
    last_login: datetime | None
    department_id: int | None = None


@dataclass(frozen=True, slots=True)
class TemporaryPasswordResult:
    """A new account or a reset password. The temporary password is shown once, to the
    administrator, and never stored in clear."""

    user: UserDTO
    temporary_password: str


@dataclass(frozen=True, slots=True)
class DeviceDTO:
    id: int
    platform: str
    last_seen: datetime


@dataclass(frozen=True, slots=True)
class NewAccount:
    """The values of an account about to be created."""

    username: str
    full_name_ar: str
    full_name_en: str
    phone: str
    university_id: str | None
    password_hash: str
    must_change_password: bool
    roles: frozenset[str]
    department_id: int | None = None


@dataclass(frozen=True, slots=True)
class UserDetails:
    """The details of a user the administrator can edit (DB-02)."""

    full_name_ar: str
    full_name_en: str
    phone: str
    university_id: str | None
    department_id: int | None = None
