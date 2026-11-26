"""Reads of the accounts module. A user reads only their own account here; the user list of
the dashboard (P0.4) is for the system administrator."""

from collections.abc import Sequence

from apps.core.domain.errors import NotFoundError
from apps.setup.application.dtos import DepartmentDTO

from .dtos import AuthContext, UserDTO
from .ports import AccountRepository, AuthContextReader, SetupFacade


class GetProfile:
    """``GET /me/``: the user's own profile and roles."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    def execute(self, user_id: int) -> UserDTO:
        user = self._accounts.to_dto(user_id)
        if user is None:
            raise NotFoundError()
        return user


class GetAuthContext:
    """Roles and the password gate of the user making a request; ``None`` for a user that no
    longer exists or was deactivated."""

    def __init__(self, reader: AuthContextReader) -> None:
        self._reader = reader

    def execute(self, user_id: int) -> AuthContext | None:
        return self._reader.auth_context(user_id)


class ListDepartments:
    """The departments a user can belong to (the user screens' choices, DB-02)."""

    def __init__(self, setup: SetupFacade) -> None:
        self._setup = setup

    def execute(self) -> Sequence[DepartmentDTO]:
        return self._setup.list_departments()
