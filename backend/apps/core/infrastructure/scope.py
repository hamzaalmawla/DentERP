"""Row scope in the ORM (design section 8, layer 2): which rows each role may see.

A repository describes its scope once, as one rule per role, and reads every row through it:

    PATIENT_SCOPE = RoleScope({
        "student": lambda actor: Q(assignments__student_id=actor.user_id,
                                   assignments__active=True),
        "management": EVERYTHING,
    })

    def get_in_scope(self, actor, pk):
        patient = PATIENT_SCOPE.get(Patient.objects, actor, pk)
        return to_dto(patient) if patient else None

A role with no rule sees nothing, so a new role never sees rows by accident.
"""

from collections.abc import Callable, Mapping

from django.db.models import Model, Q, QuerySet

from apps.core.application.dtos import Actor

type ScopeRule = Callable[[Actor], Q]


def EVERYTHING(actor: Actor) -> Q:
    """The rule for roles that see every row (management)."""
    return Q()


class RoleScope:
    def __init__(self, rules: Mapping[str, ScopeRule]) -> None:
        self._rules = dict(rules)

    def filter(self, queryset: QuerySet, actor: Actor) -> QuerySet:
        rule = self._rules.get(actor.role)
        if rule is None:
            return queryset.none()
        return queryset.filter(rule(actor)).distinct()

    def get(self, queryset: QuerySet, actor: Actor, pk: int) -> Model | None:
        """The row with this id if the actor may see it, else ``None`` (which becomes a 404)."""
        return self.filter(queryset, actor).filter(pk=pk).first()
