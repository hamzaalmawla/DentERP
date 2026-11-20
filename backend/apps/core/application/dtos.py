"""Values shared by every module's services."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Actor:
    """The user a service acts for, with the role they are using now (``X-Active-Role``).

    Driving adapters (API views, dashboard actions, Celery tasks) build it and pass it to
    services and query services, which use it for permission and scope checks (section 8).
    """

    user_id: int
    role: str


@dataclass(frozen=True, slots=True)
class NotificationTarget:
    """What a notification opens when tapped, for example ``("diagnosis", 12)``."""

    kind: str
    object_id: int | str
