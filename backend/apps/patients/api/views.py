"""Patients endpoints (design section 7). Placeholders until P1.3 builds them (501)."""

from apps.accounts.api.permissions import HasAnyRole, IsSupervisor, RoleCode
from apps.core.api.placeholders import Planned, planned_view

StudentOrSupervisor = HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR)

PatientListView = planned_view(
    "patients",
    prompt="P1.3",
    get=Planned(
        StudentOrSupervisor,
        "My patients (student) or the patients in my scope",
        operation_id="patients_list",
    ),
)

PatientDetailView = planned_view(
    "patients",
    prompt="P1.3",
    get=Planned(StudentOrSupervisor, "A patient's full record with alerts"),
)

PatientTransferView = planned_view(
    "patients",
    prompt="P1.3",
    post=Planned(IsSupervisor, "Move a patient and their open cases to another student"),
)

DiagnosisQueueView = planned_view(
    "diagnosis-queue",
    prompt="P1.3",
    get=Planned(IsSupervisor, "Patients waiting in my diagnosis clinics"),
)

DiagnosisQueueAssignView = planned_view(
    "diagnosis-queue",
    prompt="P1.3",
    post=Planned(IsSupervisor, "Assign a waiting patient to a student for diagnosis"),
)
