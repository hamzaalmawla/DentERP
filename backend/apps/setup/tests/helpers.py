"""Values shared by the setup tests."""

from datetime import date, time

from apps.core.application.dtos import Actor

PASSWORD = "Strong-Pass-2026"
ADMIN = Actor(user_id=1, role="super_admin")
NOT_ADMINS = [Actor(2, role) for role in ("management", "reception", "supervisor", "student")]


def department(**values) -> dict:
    return {"name_ar": "اللبية", "name_en": "Endodontics", **values}


def clinic(**values) -> dict:
    return {
        "number": "5",
        "name_ar": "عيادة اللبية",
        "name_en": "Endo",
        "type": "treatment",
    } | values


def session(**values) -> dict:
    return {
        "clinic_type": "treatment",
        "name_ar": "الأولى",
        "name_en": "First",
        "start_time": time(8),
        "end_time": time(9, 30),
        "order": 1,
        **values,
    }


def term(**values) -> dict:
    return {
        "name": "2026-2027 Fall",
        "start_date": date(2026, 9, 14),
        "end_date": date(2027, 1, 29),
        "is_current": True,
        **values,
    }
