"""Base for scope-aware query services (design section 8, layer 2).

Reads that depend on the user go through a query service. The query service asks a repository
port for the row *within the actor's scope*; a row that does not exist and a row the actor may
not see both come back as ``None``, and both become the same 404. That way a user cannot learn
that a record outside their scope exists.

    class PatientQueries(ScopedQueryService[PatientDTO]):
        def __init__(self, patients: PatientQueryRepository) -> None:
            self._patients = patients

        def _get_in_scope(self, actor: Actor, pk: int) -> PatientDTO | None:
            return self._patients.get_in_scope(actor, pk)

        def search(self, actor: Actor, text: str) -> Sequence[PatientDTO]:
            return self._patients.search_in_scope(actor, text)

The ORM side of the same rule is ``apps.core.infrastructure.scope.RoleScope``.
"""

from abc import ABC, abstractmethod

from apps.core.domain.errors import NotFoundError

from .dtos import Actor


def found_or_404[T](item: T | None) -> T:
    """Return the item, or raise ``NotFoundError`` when it is missing or outside scope."""
    if item is None:
        raise NotFoundError()
    return item


class ScopedQueryService[T](ABC):
    """Reads one row as the actor may see it; subclasses add their own list and search methods.

    Lists need no special care: rows outside scope are simply not in them.
    """

    def get(self, actor: Actor, pk: int) -> T:
        return found_or_404(self._get_in_scope(actor, pk))

    @abstractmethod
    def _get_in_scope(self, actor: Actor, pk: int) -> T | None:
        """The row with this id if it exists and is in the actor's scope, else ``None``."""
