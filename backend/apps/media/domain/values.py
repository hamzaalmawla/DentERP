"""Values of the media module that other modules read through its DTOs."""

from enum import StrEnum


class MediaKind(StrEnum):
    PHOTO = "photo"
    XRAY = "xray"


class OwnerKind(StrEnum):
    """What a file is attached to."""

    DIAGNOSIS = "diagnosis"
    CASE = "case"
    STEP = "step"
    TICKET = "ticket"
