"""The single API exception handler (design section 7, "Errors").

Every error the API returns has the same body:

    {"code": "step_out_of_order", "message": "…", "details": {…}}

``code`` is stable so the app can react to it; ``message`` is in the request's language
(``Accept-Language``); ``details`` holds extra data, such as the invalid fields of a form.
Set as ``REST_FRAMEWORK["EXCEPTION_HANDLER"]``.
"""

from collections.abc import Mapping
from contextlib import suppress
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.settings import api_settings
from rest_framework.views import set_rollback

from apps.core.domain.errors import AccessDeniedError, ConflictError, DomainError, NotFoundError

VALIDATION_ERROR = "validation_error"

_DOMAIN_STATUS: tuple[tuple[type[DomainError], int], ...] = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (AccessDeniedError, status.HTTP_403_FORBIDDEN),
    (ConflictError, status.HTTP_409_CONFLICT),
)


def error_body(code: str, message: Any, details: Mapping[str, Any] | None = None) -> dict:
    return {"code": code, "message": str(message), "details": dict(details or {})}


def localized_message(exc: DomainError) -> str:
    """The error's message in the active language, with its placeholders filled from
    ``details``. Also used by the dashboard to show service errors on its forms."""
    message = gettext(exc.message)
    if exc.details and "%(" in message:
        # A translation with a broken placeholder still shows its text.
        with suppress(KeyError, TypeError, ValueError):
            message = message % exc.details
    return message


def exception_handler(exc: Exception, context: dict) -> Response | None:
    if isinstance(exc, DomainError):
        return _domain_error_response(exc)

    if isinstance(exc, Http404):
        # Django's message names the model ("No Patient matches…"); never show it.
        return _domain_error_response(NotFoundError())

    if isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied(*exc.args)
    elif isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))

    if isinstance(exc, exceptions.APIException):
        return _api_exception_response(exc)

    return None  # an unexpected error: Django logs it and returns 500


def _domain_error_response(exc: DomainError) -> Response:
    status_code = next(
        (code for cls, code in _DOMAIN_STATUS if isinstance(exc, cls)),
        status.HTTP_400_BAD_REQUEST,
    )

    set_rollback()
    return Response(error_body(exc.code, localized_message(exc), exc.details), status=status_code)


def _api_exception_response(exc: exceptions.APIException) -> Response:
    headers = {}
    if getattr(exc, "auth_header", None):
        headers["WWW-Authenticate"] = exc.auth_header
    if getattr(exc, "wait", None):
        headers["Retry-After"] = f"{int(exc.wait)}"

    if isinstance(exc, exceptions.ValidationError):
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = {api_settings.NON_FIELD_ERRORS_KEY: detail}
        body = error_body(VALIDATION_ERROR, _("The data sent is not valid."), _plain(detail))
    elif isinstance(exc.detail, dict):
        # For example simplejwt: {"detail": "…", "code": "token_not_valid", "messages": […]}
        detail = dict(exc.detail)
        message = detail.pop("detail", exc.default_detail)
        code = str(detail.pop("code", None) or _code_of(exc))
        body = error_body(code, message, _plain(detail))
    else:
        details = {"wait": exc.wait} if isinstance(exc, exceptions.Throttled) else {}
        body = error_body(_code_of(exc), _plain(exc.detail), details)

    set_rollback()
    return Response(body, status=exc.status_code, headers=headers)


def _code_of(exc: exceptions.APIException) -> str:
    code = getattr(exc.detail, "code", None)
    return str(code or exc.default_code)


def _plain(value: Any) -> Any:
    """Error details as plain JSON (DRF's ``ErrorDetail`` strings become ``str``)."""
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if isinstance(value, str):
        return str(value)
    return value
