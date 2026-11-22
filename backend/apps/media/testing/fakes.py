"""In-memory fake of the media facade, for other modules' service tests.

media = InMemoryMediaFacade()
photo = media.add_media(MediaDTO(21, MediaKind.PHOTO, uploaded_by_id=40))
service = SubmitStep(..., media=media)
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _
from apps.media.application.dtos import MediaDTO, MediaOwner, SignedUrlDTO

SIGNED_URL_LIFETIME = timedelta(minutes=10)


class InMemoryMediaFacade:
    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
        self.files: dict[int, MediaDTO] = {}

    def add_media(self, media: MediaDTO) -> MediaDTO:
        self.files[media.id] = media
        return media

    # --- MediaFacade --------------------------------------------------------------------

    def get_media(self, media_ids: Sequence[int]) -> Sequence[MediaDTO]:
        try:
            return tuple(self.files[pk] for pk in media_ids)
        except KeyError:
            raise NotFoundError() from None

    def attach(self, media_ids: Sequence[int], owner: MediaOwner) -> Sequence[MediaDTO]:
        files = self.get_media(media_ids)
        if any(f.owner is not None and f.owner != owner for f in files):
            raise DomainError(
                "media_already_attached", _("A photo is already attached to another record.")
            )
        for media in files:
            self.files[media.id] = replace(media, owner=owner)
        return self.get_media(media_ids)

    def media_of(self, owner: MediaOwner) -> Sequence[MediaDTO]:
        return tuple(media for media in self.files.values() if media.owner == owner)

    def signed_url(self, media_id: int) -> SignedUrlDTO:
        media = self.get_media([media_id])[0]
        return SignedUrlDTO(
            media_id=media.id,
            url=f"memory://media/{media.id}",
            expires_at=self.now + SIGNED_URL_LIFETIME,
            thumbnail_url=f"memory://media/{media.id}/thumbnail" if media.has_thumbnail else None,
        )
