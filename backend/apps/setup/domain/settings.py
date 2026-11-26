"""System settings (SRS section 4, DB-18): the values the super admin sets once for the whole
system. Each is stored as JSON under its key (``SystemSetting``); this module says which keys
exist, what each holds and how it is checked.

The university's logo stays in ``SPU_BRAND`` (static files) in Release 1.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import time
from enum import StrEnum
from typing import Any

from apps.core.domain.i18n import _

from .errors import InvalidValueError

# Not a setting the admin edits: the number the app compares to decide whether to download
# the lookup lists again (``GET /lookups/``).
LOOKUPS_VERSION_KEY = "lookups_version"


class SettingType(StrEnum):
    TEXT = "text"
    LANGUAGE = "language"
    WHOLE_NUMBER = "whole_number"
    SWITCH = "switch"
    TIME = "time"


@dataclass(frozen=True, slots=True)
class SettingDefinition:
    key: str
    type: SettingType
    label: str
    minimum: int = 0
    maximum: int = 0
    # Sent to the app with the lookup lists; a change makes the app download them again.
    in_lookups: bool = False


LANGUAGES = ("ar", "en")

SETTINGS: tuple[SettingDefinition, ...] = (
    SettingDefinition("university_name_ar", SettingType.TEXT, _("University name (Arabic)")),
    SettingDefinition("university_name_en", SettingType.TEXT, _("University name (English)")),
    SettingDefinition("faculty_name_ar", SettingType.TEXT, _("Faculty name (Arabic)")),
    SettingDefinition("faculty_name_en", SettingType.TEXT, _("Faculty name (English)")),
    SettingDefinition("default_language", SettingType.LANGUAGE, _("Default language")),
    SettingDefinition(
        "photo_max_mb",
        SettingType.WHOLE_NUMBER,
        _("Largest photo (MB)"),
        minimum=1,
        maximum=20,
        in_lookups=True,
    ),
    SettingDefinition(
        "push_notifications_enabled", SettingType.SWITCH, _("Send push notifications")
    ),
    SettingDefinition(
        "round_morning_start", SettingType.TIME, _("Morning round starts"), in_lookups=True
    ),
    SettingDefinition(
        "round_morning_end", SettingType.TIME, _("Morning round ends"), in_lookups=True
    ),
    SettingDefinition(
        "round_afternoon_start", SettingType.TIME, _("Afternoon round starts"), in_lookups=True
    ),
    SettingDefinition(
        "round_afternoon_end", SettingType.TIME, _("Afternoon round ends"), in_lookups=True
    ),
)

SETTINGS_BY_KEY: Mapping[str, SettingDefinition] = {s.key: s for s in SETTINGS}

# (start, end) pairs whose end must come after the start.
_WINDOWS = (
    ("round_morning_start", "round_morning_end"),
    ("round_afternoon_start", "round_afternoon_end"),
)


def time_value(value: Any) -> time | None:
    """A stored time ("08:30") as a ``time``; ``None`` when it is not one."""
    if isinstance(value, time):
        return value
    try:
        return time.fromisoformat(str(value))
    except ValueError:
        return None


def _clean_one(definition: SettingDefinition, value: Any) -> Any:
    key = definition.key
    match definition.type:
        case SettingType.TEXT:
            text = str(value or "").strip()
            if not text:
                raise InvalidValueError("value_required", _("This value is required."), key)
            if len(text) > 200:
                raise InvalidValueError(
                    "too_long",
                    _("This value is too long (%(max)s characters at most)."),
                    key,
                    max=200,
                )
            return text
        case SettingType.LANGUAGE:
            if value not in LANGUAGES:
                raise InvalidValueError(
                    "choice_invalid", _("Choose one of the listed values."), key
                )
            return value
        case SettingType.WHOLE_NUMBER:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not definition.minimum <= value <= definition.maximum
            ):
                raise InvalidValueError(
                    "number_invalid",
                    _("Enter a whole number from %(minimum)s to %(maximum)s."),
                    key,
                    minimum=definition.minimum,
                    maximum=definition.maximum,
                )
            return value
        case SettingType.SWITCH:
            return bool(value)
        case SettingType.TIME:
            parsed = time_value(value) if value not in (None, "") else None
            if parsed is None:
                raise InvalidValueError("value_required", _("This value is required."), key)
            return parsed.strftime("%H:%M")
    raise AssertionError(definition.type)  # pragma: no cover


def clean_settings(values: Mapping[str, Any]) -> dict[str, Any]:
    """The settings in ``values``, checked and turned into their stored (JSON) form.

    Every key must be a known setting. Raises ``InvalidValueError`` naming the first setting
    that breaks a rule, including a round that ends before it starts.
    """
    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        definition = SETTINGS_BY_KEY.get(key)
        if definition is None:
            raise InvalidValueError("setting_unknown", _("This setting does not exist."), key)
        cleaned[key] = _clean_one(definition, value)
    return cleaned


def check_windows(settings: Mapping[str, Any]) -> None:
    """Each round must end after it starts. ``settings`` holds the stored values after the
    change."""
    for start_key, end_key in _WINDOWS:
        start, end = time_value(settings.get(start_key)), time_value(settings.get(end_key))
        if start is not None and end is not None and end <= start:
            raise InvalidValueError(
                "round_times_invalid", _("The round must end after it starts."), end_key
            )
