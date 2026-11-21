"""Password adapters over Django's hashers and password validators (AUTH_PASSWORD_VALIDATORS)."""

import secrets
import string
from collections.abc import Sequence

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.accounts.domain.accounts import Account
from apps.accounts.models import User


class DjangoPasswordHasher:
    def hash(self, raw_password: str) -> str:
        return make_password(raw_password)

    def verify(self, raw_password: str, password_hash: str) -> bool:
        return check_password(raw_password, password_hash)

    def spend_time(self, raw_password: str) -> None:
        make_password(raw_password)


class DjangoPasswordPolicy:
    """The validators in ``AUTH_PASSWORD_VALIDATORS``; messages in the active language."""

    def problems(self, raw_password: str, account: Account) -> Sequence[str]:
        # The similarity validator reads the field names from the model, so it needs a User.
        user = User(
            username=account.username,
            full_name_ar=account.full_name_ar,
            full_name_en=account.full_name_en,
            university_id=account.university_id,
        )
        try:
            validate_password(raw_password, user=user)
        except ValidationError as error:
            return [str(message) for message in error.messages]
        return []


class SecretsPasswordGenerator:
    """Random temporary passwords: 12 characters from letters and digits that are easy to read
    out and type (no 0/O, 1/l/I). They pass the password validators."""

    ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    LENGTH = 12

    def generate(self) -> str:
        while True:
            password = "".join(secrets.choice(self.ALPHABET) for _ in range(self.LENGTH))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
            ):
                return password
