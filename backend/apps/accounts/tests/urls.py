"""Test-only endpoints guarded by each permission class (``pytest.mark.urls``)."""

from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.context import request_actor
from apps.accounts.api.permissions import (
    HasAnyRole,
    IsManagement,
    IsReception,
    IsStudent,
    IsSuperAdmin,
    IsSupervisor,
    IsTechnician,
)
from config.urls import urlpatterns as project_urlpatterns

GUARDS = {
    "super_admin": IsSuperAdmin,
    "management": IsManagement,
    "reception": IsReception,
    "supervisor": IsSupervisor,
    "student": IsStudent,
    "technician": IsTechnician,
    "clinical": HasAnyRole("student", "supervisor"),
}


def guarded(permission):
    class GuardedView(APIView):
        permission_classes = [permission]

        def get(self, request):
            actor = request_actor(request)
            return Response({"user_id": actor.user_id, "role": actor.role})

    return GuardedView.as_view()


urlpatterns = [
    *project_urlpatterns,
    *(path(f"api/v1/test/{name}/", guarded(guard)) for name, guard in GUARDS.items()),
]
