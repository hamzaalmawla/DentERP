"""Values of the patients module that other modules read through its DTOs."""

from enum import StrEnum


class AssignmentPurpose(StrEnum):
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"
