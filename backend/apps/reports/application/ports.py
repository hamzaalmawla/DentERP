"""Ports of the reports module (P0.5 outline; P1.11 may refine them inside the module).

Reports has no tables and no repositories: every figure comes from another module's facade,
read with the actor's scope.
"""

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import Clock
from apps.diagnosis.application.facade import DiagnosisFacade
from apps.maintenance.application.facade import MaintenanceFacade
from apps.patients.application.facade import PatientsFacade
from apps.referrals.application.facade import ReferralsFacade
from apps.scheduling.application.facade import SchedulingFacade
from apps.setup.application.facade import SetupFacade
from apps.workcards.application.facade import WorkcardsFacade

__all__ = [
    "AcademicsFacade",  # supervisor scope
    "Clock",
    "DiagnosisFacade",  # diagnoses waiting for approval
    "MaintenanceFacade",  # rounds and tickets (F6/F18)
    "PatientsFacade",  # patients registered, diagnosis queue
    "ReferralsFacade",  # open referrals
    "SchedulingFacade",  # distribution and attendance (F8)
    "SetupFacade",  # clinics, chairs out of service, current term
    "WorkcardsFacade",  # steps waiting for approval
]
