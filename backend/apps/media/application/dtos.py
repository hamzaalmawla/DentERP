"""What the media module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from datetime import datetime

from apps.media.domain.values import MediaKind, OwnerKind

__all__ = ["MediaDTO", "MediaKind", "MediaOwner", "OwnerKind", "SignedUrlDTO"]


@dataclass(frozen=True, slots=True)
class MediaOwner:
    """The record a file is attached to, for example ``MediaOwner(OwnerKind.STEP, 51)``.
    ``patient_id`` is given for clinical records, so the photo is found in the patient's
    record too."""

    kind: OwnerKind
    object_id: int
    patient_id: int | None = None


@dataclass(frozen=True, slots=True)
class MediaDTO:
    id: int
    kind: MediaKind
    uploaded_by_id: int
    owner: MediaOwner | None = None
    taken_at: datetime | None = None
    has_thumbnail: bool = False


@dataclass(frozen=True, slots=True)
class SignedUrlDTO:
    """Private links to a file and its thumbnail, valid until ``expires_at`` (10 minutes)."""

    media_id: int
    url: str
    expires_at: datetime
    thumbnail_url: str | None = None
