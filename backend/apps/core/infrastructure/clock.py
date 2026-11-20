"""System adapter of the ``Clock`` port."""

from datetime import date, datetime

from django.utils import timezone


class SystemClock:
    def now(self) -> datetime:
        return timezone.now()

    def today(self) -> date:
        return timezone.localdate()
