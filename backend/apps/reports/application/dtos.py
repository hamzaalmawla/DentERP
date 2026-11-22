"""What the reports module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass

__all__ = ["HomeFiguresDTO"]


@dataclass(frozen=True, slots=True)
class HomeFiguresDTO:
    """The dashboard home cards (DB-16) for one actor. A figure outside the actor's role is
    ``None`` and its card is not shown (reception sees only patients and the queue)."""

    patients_today: int | None = None
    patients_this_term: int | None = None
    diagnosis_queue: int | None = None
    open_referrals: int | None = None
    approvals_waiting: int | None = None
    chairs_out_of_service: int | None = None
