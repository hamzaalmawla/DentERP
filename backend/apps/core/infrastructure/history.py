"""Full version history of a model with django-simple-history (design section 6).

A module turns it on for a model with one line in its ``models.py``:

    class Diagnosis(BaseModel):
        ...
        history = track_history()

then runs ``make makemigrations`` for the history table. Each save writes a historical row with
the user from the current request or ``acting_as`` block. Read it with ``instance.history``.
"""

from typing import Any

from simple_history.models import HistoricalRecords

from .request_context import current_user


def _history_user(**kwargs: Any) -> Any:
    return current_user()


def track_history(**options: Any) -> HistoricalRecords:
    """A ``HistoricalRecords`` field set up for this project; options pass through."""
    return HistoricalRecords(get_user=_history_user, **options)
