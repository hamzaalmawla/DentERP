"""Setup persistence (design section 6), part of the persistence adapter: services never
import this file.

Every row is soft-deleted (``is_active``), so a deactivated clinic, chair or list item stays
on the records that used it. Unique values are unique across all rows, deactivated ones
included.
"""

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.setup.domain.values import (
    AnswerType,
    CaseKind,
    ChairStatus,
    ClinicType,
    IndexKind,
    Surface,
)

CLINIC_TYPE_CHOICES = [
    (ClinicType.DIAGNOSIS.value, _("Diagnosis")),
    (ClinicType.TREATMENT.value, _("Treatment")),
    (ClinicType.LAB.value, _("Lab")),
]
CHAIR_STATUS_CHOICES = [
    (ChairStatus.IN_SERVICE.value, _("In service")),
    (ChairStatus.OUT_OF_SERVICE.value, _("Out of service")),
]
CASE_KIND_CHOICES = [
    (CaseKind.CLINICAL.value, _("Clinical")),
    (CaseKind.LAB.value, _("Lab")),
]
ANSWER_TYPE_CHOICES = [
    (AnswerType.YES_NO.value, _("Yes / no")),
    (AnswerType.YES_NO_DETAILS.value, _("Yes / no with details")),
    (AnswerType.TEXT.value, _("Text")),
]
INDEX_KIND_CHOICES = [
    (IndexKind.CALCULUS.value, _("Calculus")),
    (IndexKind.PLAQUE.value, _("Plaque")),
]
SURFACE_CHOICES = [
    (Surface.BUCCAL.value, _("Buccal")),
    (Surface.LINGUAL.value, _("Lingual")),
]


def _name_ar():
    return models.CharField(_("name (Arabic)"), max_length=150)


def _name_en():
    return models.CharField(_("name (English)"), max_length=150)


def _order():
    return models.PositiveSmallIntegerField(_("order"), default=0, db_index=True)


class Term(BaseModel):
    name = models.CharField(_("name"), max_length=100)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    is_current = models.BooleanField(_("current term"), default=False)

    class Meta:
        verbose_name = _("term")
        verbose_name_plural = _("terms")
        ordering = ["-start_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_current"],
                condition=Q(is_current=True),
                name="setup_term_one_current",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=models.F("start_date")),
                name="setup_term_ends_after_start",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Department(BaseModel):
    name_ar = _name_ar()
    name_en = _name_en()
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("head of department"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        ordering = ["name_ar", "id"]

    def __str__(self) -> str:
        return self.name_ar


class Clinic(BaseModel):
    number = models.CharField(_("number"), max_length=10, unique=True)
    name_ar = _name_ar()
    name_en = _name_en()
    building = models.CharField(_("building"), max_length=100, blank=True)
    floor = models.CharField(_("floor"), max_length=30, blank=True)
    type = models.CharField(_("type"), max_length=20, choices=CLINIC_TYPE_CHOICES)
    department = models.ForeignKey(
        Department,
        verbose_name=_("department"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clinics",
    )

    class Meta:
        verbose_name = _("clinic")
        verbose_name_plural = _("clinics")
        ordering = [Length("number"), "number"]

    def __str__(self) -> str:
        return f"{self.number} — {self.name_ar}"


class Chair(BaseModel):
    clinic = models.ForeignKey(
        Clinic, verbose_name=_("clinic"), on_delete=models.PROTECT, related_name="chairs"
    )
    number = models.PositiveSmallIntegerField(_("number"))
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=CHAIR_STATUS_CHOICES,
        default=ChairStatus.IN_SERVICE.value,
        db_index=True,
    )

    class Meta:
        verbose_name = _("chair")
        verbose_name_plural = _("chairs")
        ordering = ["clinic_id", "number"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "number"], name="setup_chair_number_unique"),
        ]

    def __str__(self) -> str:
        return _("Chair %(number)s") % {"number": self.number}


class ChairStatusChange(BaseModel):
    """One change of a chair's status, with the reason (MT-07). Written once, never changed."""

    chair = models.ForeignKey(
        Chair, verbose_name=_("chair"), on_delete=models.PROTECT, related_name="status_changes"
    )
    from_status = models.CharField(_("from"), max_length=20, choices=CHAIR_STATUS_CHOICES)
    to_status = models.CharField(_("to"), max_length=20, choices=CHAIR_STATUS_CHOICES)
    reason = models.TextField(_("reason"))
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("by"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    at = models.DateTimeField(_("time"), default=timezone.now)

    class Meta:
        verbose_name = _("chair status change")
        verbose_name_plural = _("chair status history")
        ordering = ["at", "id"]
        indexes = [models.Index(fields=["chair", "at"], name="setup_chair_history_idx")]

    def __str__(self) -> str:
        return f"{self.chair} {self.from_status} → {self.to_status}"


class Session(BaseModel):
    """A session of the clinic day, for one clinic or for every clinic of a type."""

    clinic = models.ForeignKey(
        Clinic,
        verbose_name=_("clinic"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sessions",
    )
    clinic_type = models.CharField(  # noqa: DJ001 (NULL when the session is a clinic's own)
        _("clinic type"), max_length=20, choices=CLINIC_TYPE_CHOICES, null=True, blank=True
    )
    name_ar = _name_ar()
    name_en = _name_en()
    start_time = models.TimeField(_("starts"))
    end_time = models.TimeField(_("ends"))
    order = _order()

    class Meta:
        verbose_name = _("session")
        verbose_name_plural = _("sessions")
        ordering = ["clinic_type", "clinic_id", "order", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(clinic__isnull=True, clinic_type__isnull=False)
                | Q(clinic__isnull=False, clinic_type__isnull=True),
                name="setup_session_clinic_or_type",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=models.F("start_time")),
                name="setup_session_ends_after_start",
            ),
        ]

    def __str__(self) -> str:
        return self.name_ar


class CaseType(BaseModel):
    name_ar = _name_ar()
    name_en = _name_en()
    kind = models.CharField(_("kind"), max_length=20, choices=CASE_KIND_CHOICES)
    order = _order()

    class Meta:
        verbose_name = _("case type")
        verbose_name_plural = _("case types")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name_ar


class ToothCode(BaseModel):
    letter = models.CharField(_("letter"), max_length=1, unique=True)
    meaning_ar = models.CharField(_("meaning (Arabic)"), max_length=150)
    meaning_en = models.CharField(_("meaning (English)"), max_length=150)
    color = models.CharField(_("colour"), max_length=7)
    order = _order()

    class Meta:
        verbose_name = _("tooth code")
        verbose_name_plural = _("tooth codes")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.letter} — {self.meaning_ar}"


class MedicalHistoryItem(BaseModel):
    question_ar = models.CharField(_("question (Arabic)"), max_length=255)
    question_en = models.CharField(_("question (English)"), max_length=255)
    answer_type = models.CharField(_("answer type"), max_length=20, choices=ANSWER_TYPE_CHOICES)
    is_alert = models.BooleanField(
        _("alert"),
        default=False,
        help_text=_("A yes answer shows a red alert on every screen of the patient."),
    )
    order = _order()

    class Meta:
        verbose_name = _("medical history item")
        verbose_name_plural = _("medical history items")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question_ar


class SoftTissueSite(BaseModel):
    name_ar = _name_ar()
    name_en = _name_en()
    order = _order()

    class Meta:
        verbose_name = _("soft tissue site")
        verbose_name_plural = _("soft tissue sites")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name_ar


class IndexDefinition(BaseModel):
    """One tooth surface scored for the calculus or plaque index on F1."""

    kind = models.CharField(_("index"), max_length=20, choices=INDEX_KIND_CHOICES)
    tooth = models.PositiveSmallIntegerField(_("tooth (FDI)"))
    surface = models.CharField(_("surface"), max_length=20, choices=SURFACE_CHOICES)
    min_score = models.PositiveSmallIntegerField(_("lowest score"), default=0)
    max_score = models.PositiveSmallIntegerField(_("highest score"), default=3)
    order = _order()

    class Meta:
        verbose_name = _("index definition")
        verbose_name_plural = _("index definitions")
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "tooth", "surface"], name="setup_index_definition_unique"
            ),
            models.CheckConstraint(
                condition=Q(max_score__gt=models.F("min_score")),
                name="setup_index_score_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.tooth} {self.get_surface_display()}"


class TreatmentType(BaseModel):
    """A treatment in a plan: referred to ``department``, it becomes a case of ``case_type``."""

    name_ar = _name_ar()
    name_en = _name_en()
    department = models.ForeignKey(
        Department,
        verbose_name=_("referred to department"),
        on_delete=models.PROTECT,
        related_name="treatment_types",
    )
    case_type = models.ForeignKey(
        CaseType,
        verbose_name=_("becomes case type"),
        on_delete=models.PROTECT,
        related_name="treatment_types",
    )
    order = _order()

    class Meta:
        verbose_name = _("treatment type")
        verbose_name_plural = _("treatment types")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name_ar


class ChecklistItem(BaseModel):
    """An item of the chair round checklist (F6/F18)."""

    name_ar = _name_ar()
    name_en = _name_en()
    order = _order()

    class Meta:
        verbose_name = _("checklist item")
        verbose_name_plural = _("checklist items")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name_ar


class FaultCategory(BaseModel):
    name_ar = _name_ar()
    name_en = _name_en()
    blocks_chair = models.BooleanField(
        _("takes the chair out of service"),
        default=False,
        help_text=_("A ticket in this category takes the chair out of service (BR-12)."),
    )
    order = _order()

    class Meta:
        verbose_name = _("fault category")
        verbose_name_plural = _("fault categories")
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name_ar


class SystemSetting(BaseModel):
    """One system setting (``domain.settings``), stored as JSON under its key."""

    key = models.CharField(_("key"), max_length=100, unique=True)
    value = models.JSONField(_("value"), null=True, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        verbose_name = _("system settings")
        verbose_name_plural = _("system settings")
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key
