"""In-memory fake of the notifications facade: core's ``FakeNotifier`` plus the unread count.

Services that only send notifications take core's ``FakeNotifier`` directly.
"""

from apps.core.testing import FakeNotifier


class InMemoryNotificationsFacade(FakeNotifier):
    def __init__(self) -> None:
        super().__init__()
        self.read: dict[int, int] = {}  # user id → notifications marked read

    def unread_count(self, user_id: int) -> int:
        received = sum(1 for sent in self.sent if user_id in sent.recipient_ids)
        return received - self.read.get(user_id, 0)
