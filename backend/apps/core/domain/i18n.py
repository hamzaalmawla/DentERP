"""Marking messages for translation without importing Django.

The domain layer is plain Python. Its user-facing messages are marked with ``_`` from here,
so ``makemessages`` collects them into locale/ar, and are translated later, in the request's
language, by the API exception handler (or by any adapter that shows them).

    from apps.core.domain.i18n import _

    raise DomainError("step_out_of_order", _("Approve the earlier steps first."))
"""


def _(message: str) -> str:
    """Return the message unchanged; ``makemessages`` finds it by this name."""
    return message
