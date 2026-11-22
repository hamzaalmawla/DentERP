"""Values of the setup module that other modules read through its DTOs."""

from enum import StrEnum


class ClinicType(StrEnum):
    """The kind of clinic. Code checks the type, never a clinic's name (NFR-13)."""

    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    LAB = "lab"


class ChairStatus(StrEnum):
    IN_SERVICE = "in_service"
    OUT_OF_SERVICE = "out_of_service"


class CaseKind(StrEnum):
    CLINICAL = "clinical"
    LAB = "lab"
