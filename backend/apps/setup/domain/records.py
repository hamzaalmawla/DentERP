"""The configuration records of setup and their rules (SRS section 4, design section 6).

Every record the super admin edits in the Facilities and Lists screens is described here once:
the values it holds, how each value is checked (``clean``), which values must be unique, and
which other records it points to. The services apply these rules the same way for every table,
so the dashboard, the seed command and any later caller cannot save a record that breaks them.

Values are plain Python (``str``, ``int``, ``bool``, ``date``, ``time``, ``None``); a reference
to another record is its id, under a name ending in ``_id``.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum
from typing import Any

from apps.core.domain.i18n import _

from .errors import InvalidValueError
from .values import AnswerType, CaseKind, ClinicType, IndexKind, Surface

Values = dict[str, Any]


class Table(StrEnum):
    TERM = "term"
    DEPARTMENT = "department"
    CLINIC = "clinic"
    CHAIR = "chair"
    SESSION = "session"
    CASE_TYPE = "case_type"
    TOOTH_CODE = "tooth_code"
    MEDICAL_HISTORY_ITEM = "medical_history_item"
    SOFT_TISSUE_SITE = "soft_tissue_site"
    INDEX_DEFINITION = "index_definition"
    TREATMENT_TYPE = "treatment_type"
    CHECKLIST_ITEM = "checklist_item"
    FAULT_CATEGORY = "fault_category"


# The audit log names records "app_label.ModelName".
MODEL_NAMES: Mapping[Table, str] = {
    Table.TERM: "setup.Term",
    Table.DEPARTMENT: "setup.Department",
    Table.CLINIC: "setup.Clinic",
    Table.CHAIR: "setup.Chair",
    Table.SESSION: "setup.Session",
    Table.CASE_TYPE: "setup.CaseType",
    Table.TOOTH_CODE: "setup.ToothCode",
    Table.MEDICAL_HISTORY_ITEM: "setup.MedicalHistoryItem",
    Table.SOFT_TISSUE_SITE: "setup.SoftTissueSite",
    Table.INDEX_DEFINITION: "setup.IndexDefinition",
    Table.TREATMENT_TYPE: "setup.TreatmentType",
    Table.CHECKLIST_ITEM: "setup.ChecklistItem",
    Table.FAULT_CATEGORY: "setup.FaultCategory",
}

# The lists sent to the app by GET /lookups/. A change to any of them changes the lookups
# version, so the app downloads the lists again.
LOOKUP_TABLES = frozenset(
    {
        Table.DEPARTMENT,
        Table.SESSION,
        Table.CASE_TYPE,
        Table.TOOTH_CODE,
        Table.MEDICAL_HISTORY_ITEM,
        Table.SOFT_TISSUE_SITE,
        Table.INDEX_DEFINITION,
        Table.TREATMENT_TYPE,
        Table.CHECKLIST_ITEM,
        Table.FAULT_CATEGORY,
    }
)

# The lists the dashboard orders by dragging rows (the ``order`` value).
ORDERED_TABLES = frozenset(
    {
        Table.CASE_TYPE,
        Table.TOOTH_CODE,
        Table.MEDICAL_HISTORY_ITEM,
        Table.SOFT_TISSUE_SITE,
        Table.INDEX_DEFINITION,
        Table.TREATMENT_TYPE,
        Table.CHECKLIST_ITEM,
        Table.FAULT_CATEGORY,
    }
)


# --- Checking one value ---------------------------------------------------------------


def _text(values: Mapping[str, Any], field: str, *, max_length: int = 150) -> str:
    text = str(values.get(field) or "").strip()
    if len(text) > max_length:
        raise InvalidValueError(
            "too_long",
            _("This value is too long (%(max)s characters at most)."),
            field,
            max=max_length,
        )
    return text


def _required_text(values: Mapping[str, Any], field: str, *, max_length: int = 150) -> str:
    text = _text(values, field, max_length=max_length)
    if not text:
        raise InvalidValueError("value_required", _("This value is required."), field)
    return text


def _choice[E: StrEnum](values: Mapping[str, Any], field: str, choices: type[E]) -> E:
    try:
        return choices(values.get(field))
    except ValueError:
        raise InvalidValueError(
            "choice_invalid", _("Choose one of the listed values."), field
        ) from None


def _whole_number(
    values: Mapping[str, Any], field: str, *, minimum: int, maximum: int, default: int | None = None
) -> int:
    value = values.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise InvalidValueError(
            "number_invalid",
            _("Enter a whole number from %(minimum)s to %(maximum)s."),
            field,
            minimum=minimum,
            maximum=maximum,
        )
    return value


def _order(values: Mapping[str, Any]) -> int:
    return _whole_number(values, "order", minimum=0, maximum=32767, default=0)


def _reference(values: Mapping[str, Any], field: str, *, required: bool) -> int | None:
    value = values.get(field)
    if value is None or value == "":
        if required:
            raise InvalidValueError("value_required", _("This value is required."), field)
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidValueError("choice_invalid", _("Choose one of the listed values."), field)
    return value


def _flag(values: Mapping[str, Any], field: str) -> bool:
    return bool(values.get(field, False))


def _names(values: Mapping[str, Any], prefix: str = "name") -> Values:
    """Arabic and English names; both are required (SYS-07)."""
    return {
        f"{prefix}_ar": _required_text(values, f"{prefix}_ar"),
        f"{prefix}_en": _required_text(values, f"{prefix}_en"),
    }


# --- Checking a whole record ----------------------------------------------------------

_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_LETTER = re.compile(r"^[A-Z]$")


def is_fdi_permanent_tooth(tooth: int) -> bool:
    """FDI notation of a permanent tooth: quadrant 1 to 4, then tooth 1 to 8 (11 to 48)."""
    return 1 <= tooth // 10 <= 4 and 1 <= tooth % 10 <= 8


def _clean_term(values: Mapping[str, Any]) -> Values:
    start, end = values.get("start_date"), values.get("end_date")
    if not isinstance(start, date):
        raise InvalidValueError("value_required", _("This value is required."), "start_date")
    if not isinstance(end, date):
        raise InvalidValueError("value_required", _("This value is required."), "end_date")
    if end <= start:
        raise InvalidValueError(
            "term_dates_invalid", _("The term must end after it starts."), "end_date"
        )
    return {
        "name": _required_text(values, "name", max_length=100),
        "start_date": start,
        "end_date": end,
        "is_current": _flag(values, "is_current"),
    }


def _clean_department(values: Mapping[str, Any]) -> Values:
    return {**_names(values), "head_id": _reference(values, "head_id", required=False)}


def _clean_clinic(values: Mapping[str, Any]) -> Values:
    return {
        "number": _required_text(values, "number", max_length=10),
        **_names(values),
        "building": _text(values, "building", max_length=100),
        "floor": _text(values, "floor", max_length=30),
        "type": _choice(values, "type", ClinicType),
        "department_id": _reference(values, "department_id", required=False),
    }


def _clean_chair(values: Mapping[str, Any]) -> Values:
    return {
        "clinic_id": _reference(values, "clinic_id", required=True),
        "number": _whole_number(values, "number", minimum=1, maximum=999),
    }


def _clean_session(values: Mapping[str, Any]) -> Values:
    clinic_id = _reference(values, "clinic_id", required=False)
    clinic_type = values.get("clinic_type") or None
    if (clinic_id is None) == (clinic_type is None):
        raise InvalidValueError(
            "session_target_required",
            _("Choose either a clinic or a clinic type, not both."),
            "clinic_id",
        )
    start, end = values.get("start_time"), values.get("end_time")
    if not isinstance(start, time):
        raise InvalidValueError("value_required", _("This value is required."), "start_time")
    if not isinstance(end, time):
        raise InvalidValueError("value_required", _("This value is required."), "end_time")
    if end <= start:
        raise InvalidValueError(
            "session_times_invalid", _("The session must end after it starts."), "end_time"
        )
    return {
        "clinic_id": clinic_id,
        "clinic_type": (
            _choice(values, "clinic_type", ClinicType) if clinic_type is not None else None
        ),
        **_names(values),
        "start_time": start,
        "end_time": end,
        "order": _order(values),
    }


def _clean_case_type(values: Mapping[str, Any]) -> Values:
    return {**_names(values), "kind": _choice(values, "kind", CaseKind), "order": _order(values)}


def _clean_tooth_code(values: Mapping[str, Any]) -> Values:
    letter = _required_text(values, "letter", max_length=1).upper()
    if not _LETTER.match(letter):
        raise InvalidValueError(
            "tooth_code_letter_invalid", _("The code is one Latin letter (A to Z)."), "letter"
        )
    color = _required_text(values, "color", max_length=7)
    if not _COLOR.match(color):
        raise InvalidValueError(
            "color_invalid", _("Enter a colour as # and six hex digits, e.g. #d32f2f."), "color"
        )
    return {
        "letter": letter,
        **_names(values, "meaning"),
        "color": color.lower(),
        "order": _order(values),
    }


def _clean_medical_history_item(values: Mapping[str, Any]) -> Values:
    return {
        "question_ar": _required_text(values, "question_ar", max_length=255),
        "question_en": _required_text(values, "question_en", max_length=255),
        "answer_type": _choice(values, "answer_type", AnswerType),
        "is_alert": _flag(values, "is_alert"),
        "order": _order(values),
    }


def _clean_named_item(values: Mapping[str, Any]) -> Values:
    return {**_names(values), "order": _order(values)}


def _clean_index_definition(values: Mapping[str, Any]) -> Values:
    tooth = _whole_number(values, "tooth", minimum=11, maximum=48)
    if not is_fdi_permanent_tooth(tooth):
        raise InvalidValueError(
            "tooth_invalid", _("Enter a permanent tooth in FDI notation (11 to 48)."), "tooth"
        )
    min_score = _whole_number(values, "min_score", minimum=0, maximum=9, default=0)
    max_score = _whole_number(values, "max_score", minimum=0, maximum=9, default=3)
    if max_score <= min_score:
        raise InvalidValueError(
            "score_range_invalid",
            _("The highest score must be greater than the lowest."),
            "max_score",
        )
    return {
        "kind": _choice(values, "kind", IndexKind),
        "tooth": tooth,
        "surface": _choice(values, "surface", Surface),
        "min_score": min_score,
        "max_score": max_score,
        "order": _order(values),
    }


def _clean_treatment_type(values: Mapping[str, Any]) -> Values:
    return {
        **_names(values),
        "department_id": _reference(values, "department_id", required=True),
        "case_type_id": _reference(values, "case_type_id", required=True),
        "order": _order(values),
    }


def _clean_fault_category(values: Mapping[str, Any]) -> Values:
    return {
        **_names(values),
        "blocks_chair": _flag(values, "blocks_chair"),
        "order": _order(values),
    }


_CLEANERS: Mapping[Table, Callable[[Mapping[str, Any]], Values]] = {
    Table.TERM: _clean_term,
    Table.DEPARTMENT: _clean_department,
    Table.CLINIC: _clean_clinic,
    Table.CHAIR: _clean_chair,
    Table.SESSION: _clean_session,
    Table.CASE_TYPE: _clean_case_type,
    Table.TOOTH_CODE: _clean_tooth_code,
    Table.MEDICAL_HISTORY_ITEM: _clean_medical_history_item,
    Table.SOFT_TISSUE_SITE: _clean_named_item,
    Table.INDEX_DEFINITION: _clean_index_definition,
    Table.TREATMENT_TYPE: _clean_treatment_type,
    Table.CHECKLIST_ITEM: _clean_named_item,
    Table.FAULT_CATEGORY: _clean_fault_category,
}


def clean(table: Table, values: Mapping[str, Any]) -> Values:
    """The record's values, checked and normalised (text stripped, letters upper case, …).

    Raises ``InvalidValueError`` naming the first value that breaks a rule. Values the table
    does not hold are ignored.
    """
    return _CLEANERS[table](values)


# --- Rules across records -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UniqueRule:
    """These values together may be used by one record only, active or deactivated (so a
    deactivated record can be activated again without a clash)."""

    fields: tuple[str, ...]
    code: str
    message: str

    @property
    def field(self) -> str:
        return self.fields[-1]


UNIQUE_RULES: Mapping[Table, tuple[UniqueRule, ...]] = {
    Table.CLINIC: (
        UniqueRule(
            ("number",),
            "clinic_number_taken",
            _("Another clinic already has this number (it may be deactivated)."),
        ),
    ),
    Table.CHAIR: (
        UniqueRule(
            ("clinic_id", "number"),
            "chair_number_taken",
            _("This clinic already has a chair with this number (it may be deactivated)."),
        ),
    ),
    Table.TOOTH_CODE: (
        UniqueRule(
            ("letter",),
            "tooth_code_taken",
            _("Another tooth code already uses this letter (it may be deactivated)."),
        ),
    ),
    Table.INDEX_DEFINITION: (
        UniqueRule(
            ("kind", "tooth", "surface"),
            "index_definition_taken",
            _("This index already has this tooth and surface (it may be deactivated)."),
        ),
    ),
}


@dataclass(frozen=True, slots=True)
class Reference:
    """A value that holds the id of an active record of ``table``."""

    field: str
    table: Table
    code: str
    message: str


REFERENCES: Mapping[Table, tuple[Reference, ...]] = {
    Table.CLINIC: (
        Reference(
            "department_id",
            Table.DEPARTMENT,
            "department_not_found",
            _("The department was not found or is deactivated."),
        ),
    ),
    Table.CHAIR: (
        Reference(
            "clinic_id",
            Table.CLINIC,
            "clinic_not_found",
            _("The clinic was not found or is deactivated."),
        ),
    ),
    Table.SESSION: (
        Reference(
            "clinic_id",
            Table.CLINIC,
            "clinic_not_found",
            _("The clinic was not found or is deactivated."),
        ),
    ),
    Table.TREATMENT_TYPE: (
        Reference(
            "department_id",
            Table.DEPARTMENT,
            "department_not_found",
            _("The department was not found or is deactivated."),
        ),
        Reference(
            "case_type_id",
            Table.CASE_TYPE,
            "case_type_not_found",
            _("The case type was not found or is deactivated."),
        ),
    ),
}

# Values set when a record is created that never change afterwards (a chair stays in its
# clinic; its history would otherwise move with it).
FIXED_AFTER_CREATE: Mapping[Table, tuple[str, ...]] = {Table.CHAIR: ("clinic_id",)}
