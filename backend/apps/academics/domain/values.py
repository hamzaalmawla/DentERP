"""Values of the academics module that other modules read through its DTOs."""

from enum import StrEnum


class CourseType(StrEnum):
    CLINICAL = "clinical"
    LAB = "lab"


class GradingType(StrEnum):
    NUMERIC = "numeric"
    CODE = "code"
    PASS_FAIL = "pass_fail"
