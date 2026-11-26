"""Setup endpoints (design section 7). Each view calls one query service and serializes the
DTOs it returns."""

from django.utils.cache import patch_vary_headers
from django.utils.translation import get_language
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import AnyRole
from apps.core.api.serializers import ErrorSerializer
from apps.setup import container
from apps.setup.domain.values import ClinicType

from .serializers import (
    ClinicQuerySerializer,
    ClinicSerializer,
    ClinicWithChairsSerializer,
    LookupsSerializer,
    clinic_with_chairs,
)

ERRORS = {401: ErrorSerializer, 403: ErrorSerializer}


def _language() -> str:
    return (get_language() or "ar").split("-")[0]


def lookups_etag(version: int, language: str) -> str:
    """The lists differ by version and by language, so both are in the ETag."""
    return f'"lookups-{version}-{language}"'


def _etag_matches(request, etag: str) -> bool:
    sent = request.headers.get("If-None-Match", "")
    return any(tag.strip().removeprefix("W/") in (etag, "*") for tag in sent.split(","))


class LookupsView(APIView):
    permission_classes = [AnyRole]

    @extend_schema(
        tags=["lookups"],
        summary="Every lookup list in one call",
        description="Tooth codes, medical history items, soft tissue sites, index set, "
        "departments, case and treatment types, checklist, fault categories, sessions and the "
        "settings the app needs, active rows only and in order. Names are in the request "
        "language (Accept-Language). The ETag changes with the version and the language: send "
        "it back in If-None-Match and the answer is 304 with no body while nothing changed.",
        parameters=[
            OpenApiParameter("If-None-Match", OpenApiTypes.STR, OpenApiParameter.HEADER),
        ],
        responses={
            200: LookupsSerializer,
            304: OpenApiResponse(description="The lists have not changed."),
            **ERRORS,
        },
    )
    def get(self, request):
        language = _language()
        etag = lookups_etag(container.get_lookups_version().execute(), language)
        if _etag_matches(request, etag):
            response = Response(status=status.HTTP_304_NOT_MODIFIED)
        else:
            lookups = container.get_lookups().execute()
            # The version read with the lists, in case a list changed in between.
            etag = lookups_etag(lookups.version, language)
            response = Response(LookupsSerializer(lookups).data)
        response["ETag"] = etag
        response["Cache-Control"] = "private, no-cache"
        patch_vary_headers(response, ["Accept-Language"])
        return response


class ClinicListView(APIView):
    permission_classes = [AnyRole]

    @extend_schema(
        tags=["clinics"],
        summary="Clinics, optionally with their chairs",
        description="Active clinics by number, names in the request language. "
        "with=chair_status adds each clinic's active chairs with their status and the counts "
        "in and out of service (the technician's round, MT-02).",
        parameters=[
            OpenApiParameter("type", OpenApiTypes.STR, enum=[t.value for t in ClinicType]),
            OpenApiParameter("with", OpenApiTypes.STR, enum=["chair_status"]),
        ],
        responses={200: ClinicWithChairsSerializer(many=True), 400: ErrorSerializer, **ERRORS},
    )
    def get(self, request):
        query = ClinicQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        clinic_type = query.validated_data.get("type")
        clinic_type = ClinicType(clinic_type) if clinic_type else None
        clinics = container.list_clinics()
        if query.validated_data.get("with") == "chair_status":
            body = [clinic_with_chairs(item) for item in clinics.with_chairs(type=clinic_type)]
        else:
            body = ClinicSerializer(clinics.execute(type=clinic_type), many=True).data
        response = Response(body)
        patch_vary_headers(response, ["Accept-Language"])
        return response
