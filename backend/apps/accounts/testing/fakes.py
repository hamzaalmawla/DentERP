"""In-memory fakes of the ports in ``apps.accounts.application.ports``.

They keep the same rules as the real adapters (only active users are found, usernames are
never reused, a revoked token stays revoked), so a service behaves the same with either.
"""

import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from apps.accounts.application.dtos import AuthContext, DeviceDTO, NewAccount, TokenPair, UserDTO
from apps.accounts.domain.accounts import Account
from apps.accounts.domain.errors import InvalidTokenError
from apps.accounts.domain.roles import ALL_ROLES


@dataclass
class _StoredUser:
    account: Account
    phone: str = ""
    is_active: bool = True
    roles: set[str] = field(default_factory=set)


class InMemoryAccountRepository:
    def __init__(self) -> None:
        self.users: dict[int, _StoredUser] = {}
        self._ids = itertools.count(1)

    # Test helpers -------------------------------------------------------------------

    def add(
        self,
        username: str = "user",
        *,
        password_hash: str = "hashed:Old-Pass-2026",
        roles: Iterable[str] = ("student",),
        is_active: bool = True,
        **values,
    ) -> Account:
        user_id = next(self._ids)
        phone = values.pop("phone", "")
        account = Account(id=user_id, username=username, password_hash=password_hash, **values)
        self.users[user_id] = _StoredUser(account, phone, is_active, set(roles))
        return account

    def stored(self, user_id: int) -> Account:
        return self.users[user_id].account

    # Port -----------------------------------------------------------------------------

    def get(self, user_id: int, *, for_update: bool = False) -> Account | None:
        stored = self.users.get(user_id)
        return stored.account if stored and stored.is_active else None

    def get_by_username(self, username: str, *, for_update: bool = False) -> Account | None:
        return next(
            (
                s.account
                for s in self.users.values()
                if s.is_active and s.account.username == username
            ),
            None,
        )

    def save(self, account: Account) -> None:
        self.users[account.id].account = account

    def create(self, account: NewAccount) -> int:
        user_id = next(self._ids)
        self.users[user_id] = _StoredUser(
            Account(
                id=user_id,
                username=account.username,
                password_hash=account.password_hash,
                must_change_password=account.must_change_password,
                full_name_ar=account.full_name_ar,
                full_name_en=account.full_name_en,
                university_id=account.university_id,
            ),
            phone=account.phone,
            roles=set(account.roles),
        )
        return user_id

    def username_exists(self, username: str) -> bool:
        return any(s.account.username == username for s in self.users.values())

    def university_id_exists(self, university_id: str) -> bool:
        return any(s.account.university_id == university_id for s in self.users.values())

    def roles_of(self, user_id: int) -> frozenset[str]:
        stored = self.users.get(user_id)
        return frozenset(stored.roles) if stored and stored.is_active else frozenset()

    def set_roles(self, user_id: int, roles: Iterable[str]) -> None:
        self.users[user_id].roles = set(roles)

    def to_dto(self, user_id: int) -> UserDTO | None:
        stored = self.users.get(user_id)
        if stored is None or not stored.is_active:
            return None
        account = stored.account
        return UserDTO(
            id=account.id,
            username=account.username,
            full_name_ar=account.full_name_ar,
            full_name_en=account.full_name_en,
            phone=stored.phone,
            university_id=account.university_id,
            roles=tuple(sorted(stored.roles)),
            must_change_password=account.must_change_password,
            locked_until=account.locked_until,
            last_login=account.last_login,
        )


class InMemoryRoleRepository:
    def __init__(self, codes: Iterable[str] = ALL_ROLES) -> None:
        self.codes = frozenset(codes)

    def active_codes(self) -> frozenset[str]:
        return self.codes


class InMemoryAuthContextReader:
    def __init__(self, accounts: InMemoryAccountRepository) -> None:
        self._accounts = accounts

    def auth_context(self, user_id: int) -> AuthContext | None:
        account = self._accounts.get(user_id)
        if account is None:
            return None
        return AuthContext(
            user_id=user_id,
            roles=self._accounts.roles_of(user_id),
            must_change_password=account.must_change_password,
        )


@dataclass
class _Device:
    id: int
    user_id: int
    platform: str
    token: str
    last_seen: datetime


class InMemoryDeviceTokenRepository:
    def __init__(self) -> None:
        self.devices: dict[str, _Device] = {}
        self._ids = itertools.count(1)

    def register(self, user_id: int, platform: str, token: str, seen_at: datetime) -> DeviceDTO:
        device = self.devices.get(token)
        if device is None:
            device = _Device(next(self._ids), user_id, platform, token, seen_at)
            self.devices[token] = device
        else:
            device.user_id, device.platform, device.last_seen = user_id, platform, seen_at
        return DeviceDTO(id=device.id, platform=device.platform, last_seen=device.last_seen)


class FakePasswordHasher:
    """``hash("x")`` is ``"hashed:x"``. Counts the hashes spent on unknown users."""

    def __init__(self) -> None:
        self.time_spent = 0

    def hash(self, raw_password: str) -> str:
        return f"hashed:{raw_password}"

    def verify(self, raw_password: str, password_hash: str) -> bool:
        return password_hash == self.hash(raw_password)

    def spend_time(self, raw_password: str) -> None:
        self.time_spent += 1


class FakePasswordPolicy:
    """Refuses passwords shorter than 8 characters, and any password in ``refused``."""

    def __init__(self, refused: Iterable[str] = ()) -> None:
        self.refused = set(refused)

    def problems(self, raw_password: str, account: Account) -> Sequence[str]:
        problems = []
        if len(raw_password) < 8:
            problems.append("too short")
        if raw_password in self.refused:
            problems.append("too common")
        return problems


class FixedPasswordGenerator:
    def __init__(self, password: str = "Temp-Pass-4821") -> None:
        self.password = password

    def generate(self) -> str:
        return self.password


@dataclass(frozen=True)
class _IssuedToken:
    user_id: int
    refresh: str


class FakeTokenIssuer:
    """Tokens are ``"access-N"`` / ``"refresh-N"``; revoked refresh tokens stay revoked."""

    def __init__(self) -> None:
        self._counter = itertools.count(1)
        self.issued: dict[str, int] = {}  # refresh token → user id
        self.revoked: set[str] = set()

    def issue(self, user_id: int) -> TokenPair:
        n = next(self._counter)
        refresh = f"refresh-{n}"
        self.issued[refresh] = user_id
        return TokenPair(access=f"access-{n}", refresh=refresh)

    def user_of(self, refresh: str) -> int:
        if refresh not in self.issued or refresh in self.revoked:
            raise InvalidTokenError()
        return self.issued[refresh]

    def rotate(self, refresh: str) -> TokenPair:
        user_id = self.user_of(refresh)
        self.revoked.add(refresh)
        return self.issue(user_id)

    def revoke(self, refresh: str) -> int:
        user_id = self.user_of(refresh)
        self.revoked.add(refresh)
        return user_id

    def revoke_all(self, user_id: int) -> None:
        self.revoked.update(t for t, owner in self.issued.items() if owner == user_id)

    def open_tokens(self, user_id: int) -> set[str]:
        return {t for t, owner in self.issued.items() if owner == user_id} - self.revoked
