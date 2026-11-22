"""The media module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never media's models or repositories. Every function takes and
returns ids and DTOs. A missing file raises ``NotFoundError``.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from .dtos import MediaDTO, MediaOwner, SignedUrlDTO


@runtime_checkable
class MediaFacade(Protocol):
    def get_media(self, media_ids: Sequence[int]) -> Sequence[MediaDTO]:
        """The files in the order of the ids (for example to check that a step has the photo
        or X-ray its template needs); ``NotFoundError`` if one is missing."""
        ...

    def attach(self, media_ids: Sequence[int], owner: MediaOwner) -> Sequence[MediaDTO]:
        """Link uploaded files to their record. Attaching a file again to the same owner
        changes nothing; a file attached to another owner refuses with
        ``DomainError("media_already_attached")``."""
        ...

    def media_of(self, owner: MediaOwner) -> Sequence[MediaDTO]: ...

    def signed_url(self, media_id: int) -> SignedUrlDTO:
        """Links to the file and its thumbnail that expire after 10 minutes. The caller has
        already checked that the user may see the owner."""
        ...


class MediaFacadeService:
    """The media facade the container hands out. Built in P1.5."""

    def get_media(self, media_ids: Sequence[int]) -> Sequence[MediaDTO]:
        raise NotImplementedError

    def attach(self, media_ids: Sequence[int], owner: MediaOwner) -> Sequence[MediaDTO]:
        raise NotImplementedError

    def media_of(self, owner: MediaOwner) -> Sequence[MediaDTO]:
        raise NotImplementedError

    def signed_url(self, media_id: int) -> SignedUrlDTO:
        raise NotImplementedError
