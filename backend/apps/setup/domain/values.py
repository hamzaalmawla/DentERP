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


class AnswerType(StrEnum):
    """How a medical history question is answered on F1."""

    YES_NO = "yes_no"
    YES_NO_DETAILS = "yes_no_details"
    TEXT = "text"


class IndexKind(StrEnum):
    """The oral hygiene indices of F1."""

    CALCULUS = "calculus"
    PLAQUE = "plaque"


class Surface(StrEnum):
    BUCCAL = "buccal"
    LINGUAL = "lingual"
