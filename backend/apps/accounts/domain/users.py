"""Rules for the user records the system administrator keeps (DB-02)."""

import re

from .errors import FullNameRequiredError, InvalidUsernameError

MAX_USERNAME_LENGTH = 150
_USERNAME = re.compile(r"^[\w.@+-]+$")


def validate_username(username: str) -> str:
    """A normalised username: letters, digits and ``. @ + - _``, at most 150 characters."""
    if not username or len(username) > MAX_USERNAME_LENGTH or not _USERNAME.match(username):
        raise InvalidUsernameError()
    return username


def validate_full_name(full_name_ar: str) -> str:
    name = full_name_ar.strip()
    if not name:
        raise FullNameRequiredError()
    return name
