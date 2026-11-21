"""The login rules (SYS-01, ST-01): lockout after failed logins and the temporary password."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .errors import AccountLockedError

MAX_FAILED_LOGINS = 5
LOCK_DURATION = timedelta(minutes=15)


def normalize_username(username: str) -> str:
    """Usernames are compared without case or surrounding spaces (phone keyboards capitalise
    the first letter)."""
    return username.strip().lower()


@dataclass(frozen=True, slots=True)
class Account:
    """A user account as the login rules see it."""

    id: int
    username: str
    password_hash: str
    must_change_password: bool = False
    failed_logins: int = 0
    locked_until: datetime | None = None
    last_login: datetime | None = None
    full_name_ar: str = ""
    full_name_en: str = ""
    university_id: str | None = None

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now

    def ensure_not_locked(self, now: datetime) -> None:
        if self.is_locked(now):
            raise AccountLockedError(self.locked_until)

    def after_failed_login(self, now: datetime) -> "Account":
        """One more failed login. The 5th in a row locks the account for 15 minutes.

        Failures before a lock that has already run out are forgotten, so the next lock again
        needs 5 failures.
        """
        failed = 0 if self.locked_until is not None else self.failed_logins
        failed += 1
        if failed >= MAX_FAILED_LOGINS:
            return replace(self, failed_logins=failed, locked_until=now + LOCK_DURATION)
        return replace(self, failed_logins=failed, locked_until=None)

    def after_successful_login(self, now: datetime) -> "Account":
        return replace(self, failed_logins=0, locked_until=None, last_login=now)

    def unlocked(self) -> "Account":
        return replace(self, failed_logins=0, locked_until=None)

    def with_password(self, password_hash: str, *, temporary: bool) -> "Account":
        """A new password. A temporary one (set by the administrator) must be changed at the
        next login."""
        return replace(self, password_hash=password_hash, must_change_password=temporary)
