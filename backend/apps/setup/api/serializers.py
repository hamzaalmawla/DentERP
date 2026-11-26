"""Response bodies of the setup endpoints, built from DTOs.

Names are sent in the request's language (``Accept-Language``): ``name`` is the Arabic or the
English name, never both (design section 7).
"""

from django.utils.translation import get_language
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.setup.domain.values import (
    AnswerType,
    CaseKind,
    ChairStatus,
    ClinicType,
    IndexKind,
    Surface,
)

# One enum each in the OpenAPI schema (SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]).
CLINIC_TYPE_CHOICES = [value.value for value in ClinicType]
CHAIR_STATUS_CHOICES = [value.value for value in ChairStatus]
CASE_KIND_CHOICES = [value.value for value in CaseKind]
ANSWER_TYPE_CHOICES = [value.value for value in AnswerType]
INDEX_KIND_CHOICES = [value.value for value in IndexKind]
SURFACE_CHOICES = [value.value for value in Surface]


def in_request_language(arabic: str, english: str) -> str:
    """The English text for an English request when there is one; otherwise the Arabic."""
    language = (get_language() or "ar").split("-")[0]
    return english if language == "en" and english else arabic


@extend_schema_field(OpenApiTypes.STR)
class LocalizedField(serializers.Field):
    """``<prefix>_ar`` or ``<prefix>_en`` of the object, in the request's language."""

    def __init__(self, prefix: str = "name", **kwargs) -> None:
        self.prefix = prefix
        kwargs.update(source="*", read_only=True)
        super().__init__(**kwargs)

    def to_representation(self, value) -> str:
        return in_request_language(
            getattr(value, f"{self.prefix}_ar"), getattr(value, f"{self.prefix}_en")
        )


class NamedItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = LocalizedField()


class CaseTypeSerializer(NamedItemSerializer):
    kind = serializers.ChoiceField(choices=CASE_KIND_CHOICES)


class TreatmentTypeSerializer(NamedItemSerializer):
    department_id = serializers.IntegerField()
    case_type_id = serializers.IntegerField()


class ToothCodeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    letter = serializers.CharField()
    meaning = LocalizedField("meaning")
    color = serializers.CharField(help_text="Colour on the dental chart, #rrggbb.")


class MedicalHistoryItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    question = LocalizedField("question")
    answer_type = serializers.ChoiceField(choices=ANSWER_TYPE_CHOICES)
    is_alert = serializers.BooleanField(
        help_text="A yes answer shows a red alert on every screen of the patient (US-12)."
    )


class IndexDefinitionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=INDEX_KIND_CHOICES)
    tooth = serializers.IntegerField(help_text="FDI tooth number.")
    surface = serializers.ChoiceField(choices=SURFACE_CHOICES)
    min_score = serializers.IntegerField()
    max_score = serializers.IntegerField()


class FaultCategorySerializer(NamedItemSerializer):
    blocks_chair = serializers.BooleanField(
        help_text="A ticket in this category takes the chair out of service."
    )


class SessionSerializer(NamedItemSerializer):
    start_time = serializers.TimeField(format="%H:%M")
    end_time = serializers.TimeField(format="%H:%M")
    clinic_id = serializers.IntegerField(
        allow_null=True, help_text="Set when the session belongs to one clinic."
    )
    clinic_type = serializers.ChoiceField(
        choices=CLINIC_TYPE_CHOICES,
        allow_null=True,
        help_text="Set when the session belongs to every clinic of this type without sessions "
        "of its own.",
    )


class LookupSettingsSerializer(serializers.Serializer):
    photo_max_mb = serializers.IntegerField(allow_null=True)
    round_morning_start = serializers.CharField(allow_null=True, help_text="HH:MM")
    round_morning_end = serializers.CharField(allow_null=True, help_text="HH:MM")
    round_afternoon_start = serializers.CharField(allow_null=True, help_text="HH:MM")
    round_afternoon_end = serializers.CharField(allow_null=True, help_text="HH:MM")


class LookupsSerializer(serializers.Serializer):
    version = serializers.IntegerField(
        help_text="Changes whenever a list changes; also sent as the ETag."
    )
    departments = NamedItemSerializer(many=True)
    case_types = CaseTypeSerializer(many=True)
    treatment_types = TreatmentTypeSerializer(many=True)
    tooth_codes = ToothCodeSerializer(many=True)
    medical_history_items = MedicalHistoryItemSerializer(many=True)
    soft_tissue_sites = NamedItemSerializer(many=True)
    index_definitions = IndexDefinitionSerializer(many=True)
    checklist_items = NamedItemSerializer(many=True)
    fault_categories = FaultCategorySerializer(many=True)
    sessions = SessionSerializer(many=True)
    settings = LookupSettingsSerializer()


class ClinicQuerySerializer(serializers.Serializer):
    """``?type=`` and ``?with=`` (a Python keyword, so the fields are built here)."""

    def get_fields(self):
        return {
            "type": serializers.ChoiceField(choices=CLINIC_TYPE_CHOICES, required=False),
            "with": serializers.ChoiceField(choices=["chair_status"], required=False),
        }


class ClinicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.CharField()
    name = LocalizedField()
    type = serializers.ChoiceField(choices=CLINIC_TYPE_CHOICES)
    department_id = serializers.IntegerField(allow_null=True)
    building = serializers.CharField()
    floor = serializers.CharField()


class ChairSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.IntegerField()
    status = serializers.ChoiceField(choices=CHAIR_STATUS_CHOICES)


class ClinicWithChairsSerializer(ClinicSerializer):
    """With ``?with=chair_status``."""

    chairs_in_service = serializers.IntegerField(required=False)
    chairs_out_of_service = serializers.IntegerField(required=False)
    chairs = ChairSerializer(many=True, required=False)


def clinic_with_chairs(item) -> dict:
    """The body of one clinic with its chairs (a ``ClinicChairsDTO``)."""
    return {
        **ClinicSerializer(item.clinic).data,
        "chairs_in_service": item.in_service_count,
        "chairs_out_of_service": item.out_of_service_count,
        "chairs": ChairSerializer(item.chairs, many=True).data,
    }
