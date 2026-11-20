"""Adapter of the ``FileStorage`` port over Django's default storage (Garage S3 in every
environment except tests, which use in-memory storage)."""

from typing import BinaryIO

from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage, default_storage


class DjangoFileStorage:
    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage or default_storage

    def save(self, name: str, content: BinaryIO | bytes, content_type: str) -> str:
        file = ContentFile(content, name=name) if isinstance(content, bytes) else File(content)
        file.content_type = content_type
        return self._storage.save(name, file)

    def open(self, name: str) -> bytes:
        with self._storage.open(name, "rb") as file:
            return file.read()

    def exists(self, name: str) -> bool:
        return self._storage.exists(name)

    def signed_url(self, name: str, expires_in_seconds: int) -> str:
        try:
            return self._storage.url(name, expire=expires_in_seconds)
        except TypeError:  # storages without signed links (local tests) take no expiry
            return self._storage.url(name)
