"""A query service and its ORM repository, built the way modules build theirs."""

from dataclasses import dataclass

from django.db.models import Q

from apps.core.application.dtos import Actor
from apps.core.application.scope import ScopedQueryService
from apps.core.infrastructure.scope import EVERYTHING, RoleScope

from .models import Note


@dataclass(frozen=True)
class NoteDTO:
    id: int
    title: str


NOTE_SCOPE = RoleScope(
    {
        "student": lambda actor: Q(owner_id=actor.user_id),
        "management": EVERYTHING,
    }
)


class OrmNoteRepository:
    def get_in_scope(self, actor: Actor, pk: int) -> NoteDTO | None:
        note = NOTE_SCOPE.get(Note.objects, actor, pk)
        return NoteDTO(note.pk, note.title) if note else None


class NoteQueries(ScopedQueryService[NoteDTO]):
    def __init__(self, notes: OrmNoteRepository) -> None:
        self._notes = notes

    def _get_in_scope(self, actor: Actor, pk: int) -> NoteDTO | None:
        return self._notes.get_in_scope(actor, pk)
