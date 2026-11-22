"""The diagnosis module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never diagnosis' models or repositories. Every function takes and
returns ids and DTOs. A missing or inactive row raises ``NotFoundError``.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.core.application.dtos import Actor

from .dtos import DiagnosisSummaryDTO, MedicalAlertDTO, PlanItemDTO, PlanItemStatus


@runtime_checkable
class DiagnosisFacade(Protocol):
    def get_diagnosis_summary(self, diagnosis_id: int) -> DiagnosisSummaryDTO: ...

    def approved_plan_items(self, diagnosis_id: int) -> Sequence[PlanItemDTO]:
        """The plan items of an approved diagnosis. ``DomainError("diagnosis_not_approved")``
        when the diagnosis is not approved (BR-04)."""
        ...

    def get_plan_items(self, plan_item_ids: Sequence[int]) -> Sequence[PlanItemDTO]:
        """The plan items, in the order of the ids; ``NotFoundError`` if one is missing."""
        ...

    def mark_plan_items(
        self, plan_item_ids: Sequence[int], status: PlanItemStatus
    ) -> Sequence[PlanItemDTO]:
        """Move plan items to ``status``: referred (referral sent), planned (rejected),
        done (case complete, BR-08). ``DomainError("plan_item_status")`` for a move the
        plan item's state does not allow."""
        ...

    def medical_alerts(self, patient_id: int) -> Sequence[MedicalAlertDTO]:
        """The alert answers of the patient's latest approved (or in progress) diagnosis."""
        ...

    def submitted_for(self, actor: Actor) -> Sequence[DiagnosisSummaryDTO]:
        """Diagnoses waiting for approval in the supervisor's scope (the approvals queue)."""
        ...

    def can_read_diagnosis(self, actor: Actor, diagnosis_id: int) -> bool:
        """The diagnosis is in the actor's scope. Used by media for X-rays."""
        ...


class DiagnosisFacadeService:
    """The diagnosis facade the container hands out. Built in P1.4."""

    def get_diagnosis_summary(self, diagnosis_id: int) -> DiagnosisSummaryDTO:
        raise NotImplementedError

    def approved_plan_items(self, diagnosis_id: int) -> Sequence[PlanItemDTO]:
        raise NotImplementedError

    def get_plan_items(self, plan_item_ids: Sequence[int]) -> Sequence[PlanItemDTO]:
        raise NotImplementedError

    def mark_plan_items(
        self, plan_item_ids: Sequence[int], status: PlanItemStatus
    ) -> Sequence[PlanItemDTO]:
        raise NotImplementedError

    def medical_alerts(self, patient_id: int) -> Sequence[MedicalAlertDTO]:
        raise NotImplementedError

    def submitted_for(self, actor: Actor) -> Sequence[DiagnosisSummaryDTO]:
        raise NotImplementedError

    def can_read_diagnosis(self, actor: Actor, diagnosis_id: int) -> bool:
        raise NotImplementedError
