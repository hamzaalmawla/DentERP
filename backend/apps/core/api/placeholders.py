"""Placeholder endpoints for the API outline (P0.5).

Each module declares the Release 1 endpoints it will build (design section 7) with
``planned_view``. The endpoint is in the OpenAPI schema and checks the caller's role like the
real one will, then answers 501 in the standard error format:

    {"code": "not_implemented", "message": "…", "details": {"planned_in": "P1.3"}}

When a module builds the endpoint, it replaces the placeholder with its real view:

    PatientListView = planned_view(
        "patients",
        prompt="P1.3",
        get=Planned(HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR), "My patients"),
    )

Core does not know the roles (accounts owns them), so each operation receives its permission
class from the module's ``api/``.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from .serializers import ErrorSerializer

NOT_IMPLEMENTED = "not_implemented"

_METHODS = ("get", "post", "patch", "put", "delete")


class NotImplementedYet(APIException):
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_code = NOT_IMPLEMENTED
    default_detail = _("This endpoint is planned but not built yet.")


@dataclass(frozen=True)
class Planned:
    """One planned operation: who may call it and what it will do."""

    permission: type[BasePermission]
    summary: str
    parameters: Sequence[OpenApiParameter] = ()
    operation_id: str | None = None  # when drf-spectacular's guess would repeat another one


def _operation(planned: Planned, prompt: str):
    @extend_schema(
        operation_id=planned.operation_id,
        summary=planned.summary,
        description=f"Planned in {prompt}. Answers 501 not_implemented until it is built.",
        parameters=list(planned.parameters),
        request=None,
        responses={
            401: ErrorSerializer,
            403: ErrorSerializer,
            501: ErrorSerializer,
        },
    )
    def handler(self, request, *args, **kwargs):
        raise NotImplementedYet(
            {
                "detail": NotImplementedYet.default_detail,
                "code": NOT_IMPLEMENTED,
                "planned_in": prompt,
            }
        )

    return handler


def planned_view(tag: str, *, prompt: str, **operations: Planned) -> type[APIView]:
    """An API view whose operations check the role, then answer 501 ``not_implemented``.

    The permission is checked before the handler runs (DRF's ``initial``), so a role that will
    not be allowed gets 403 now, as it will later.
    """
    unknown = set(operations) - set(_METHODS)
    if not operations or unknown:
        raise ValueError(f"Unknown HTTP methods: {sorted(unknown) or 'none given'}")

    permissions = {method.upper(): planned.permission for method, planned in operations.items()}

    def get_permissions(self):
        permission = permissions.get(self.request.method)
        if permission is None:  # OPTIONS, HEAD: the defaults (logged in)
            return APIView.get_permissions(self)
        return [permission()]

    attributes = {
        "get_permissions": get_permissions,
        "planned_operations": dict(operations),
        "planned_prompt": prompt,
        **{method: _operation(planned, prompt) for method, planned in operations.items()},
    }
    return extend_schema(tags=[tag])(type(f"Planned_{tag}_View", (APIView,), attributes))
