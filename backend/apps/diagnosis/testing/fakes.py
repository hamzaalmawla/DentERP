"""In-memory fake of the diagnosis facade, for other modules' service tests.

diagnosis = InMemoryDiagnosisFacade()
diagnosis.add_diagnosis(DiagnosisSummaryDTO(4, patient_id=3, student_id=40, clinic_id=1,
                                            status=DiagnosisStatus.APPROVED, version=1))
diagnosis.add_plan_item(PlanItemDTO(9, 4, 3, treatment_type_id=2, department_id=2,
                                    status=PlanItemStatus.PLANNED, teeth=(36,)))
"""

from collections.abc import Sequence
from dataclasses import replace

from apps.core.application.dtos import Actor
from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _
from apps.diagnosis.application.dtos import (
    DiagnosisStatus,
    DiagnosisSummaryDTO,
    MedicalAlertDTO,
    PlanItemDTO,
    PlanItemStatus,
)

# The moves another module may ask for (referral sent, rejected; case complete).
_ALLOWED_MOVES = {
    PlanItemStatus.REFERRED: {PlanItemStatus.PLANNED},
    PlanItemStatus.PLANNED: {PlanItemStatus.REFERRED},
    PlanItemStatus.DONE: {PlanItemStatus.REFERRED},
    PlanItemStatus.CANCELLED: {PlanItemStatus.PLANNED},
}


class InMemoryDiagnosisFacade:
    def __init__(self) -> None:
        self.diagnoses: dict[int, DiagnosisSummaryDTO] = {}
        self.plan_items: dict[int, PlanItemDTO] = {}
        self.alerts: dict[int, list[MedicalAlertDTO]] = {}  # patient id → alerts
        self.scope: dict[int, set[int]] = {}  # supervisor id → clinic ids

    # --- Test set-up ------------------------------------------------------------------

    def add_diagnosis(self, diagnosis: DiagnosisSummaryDTO) -> DiagnosisSummaryDTO:
        self.diagnoses[diagnosis.id] = diagnosis
        return diagnosis

    def add_plan_item(self, item: PlanItemDTO) -> PlanItemDTO:
        self.plan_items[item.id] = item
        return item

    def add_alert(self, patient_id: int, alert: MedicalAlertDTO) -> MedicalAlertDTO:
        self.alerts.setdefault(patient_id, []).append(alert)
        return alert

    # --- DiagnosisFacade ----------------------------------------------------------------

    def get_diagnosis_summary(self, diagnosis_id: int) -> DiagnosisSummaryDTO:
        try:
            return self.diagnoses[diagnosis_id]
        except KeyError:
            raise NotFoundError() from None

    def approved_plan_items(self, diagnosis_id: int) -> Sequence[PlanItemDTO]:
        if self.get_diagnosis_summary(diagnosis_id).status != DiagnosisStatus.APPROVED:
            raise DomainError("diagnosis_not_approved", _("The diagnosis is not approved."))
        return tuple(i for i in self.plan_items.values() if i.diagnosis_id == diagnosis_id)

    def get_plan_items(self, plan_item_ids: Sequence[int]) -> Sequence[PlanItemDTO]:
        try:
            return tuple(self.plan_items[pk] for pk in plan_item_ids)
        except KeyError:
            raise NotFoundError() from None

    def mark_plan_items(
        self, plan_item_ids: Sequence[int], status: PlanItemStatus
    ) -> Sequence[PlanItemDTO]:
        items = self.get_plan_items(plan_item_ids)
        target = PlanItemStatus(status)
        if any(item.status not in _ALLOWED_MOVES[target] for item in items):
            raise DomainError(
                "plan_item_status", _("A plan item cannot move to this status from its own.")
            )
        for item in items:
            self.plan_items[item.id] = replace(item, status=target)
        return self.get_plan_items(plan_item_ids)

    def medical_alerts(self, patient_id: int) -> Sequence[MedicalAlertDTO]:
        return tuple(self.alerts.get(patient_id, ()))

    def submitted_for(self, actor: Actor) -> Sequence[DiagnosisSummaryDTO]:
        clinics = self.scope.get(actor.user_id, set())
        return tuple(
            d
            for d in self.diagnoses.values()
            if d.status == DiagnosisStatus.SUBMITTED and d.clinic_id in clinics
        )

    def can_read_diagnosis(self, actor: Actor, diagnosis_id: int) -> bool:
        diagnosis = self.diagnoses.get(diagnosis_id)
        return diagnosis is not None and (
            diagnosis.student_id == actor.user_id
            or diagnosis.clinic_id in self.scope.get(actor.user_id, set())
        )
