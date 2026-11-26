"""UpdateSettings (DB-18) and SeedDefaults, with in-memory fakes."""

from datetime import time

import pytest

from apps.core.domain.errors import AccessDeniedError, DomainError
from apps.setup.application.services import SeedDefaults
from apps.setup.domain.records import Table
from apps.setup.domain.settings import LOOKUPS_VERSION_KEY
from apps.setup.infrastructure.seed import JsonSeedSource
from apps.setup.testing import InMemorySeedSource

from .helpers import ADMIN, NOT_ADMINS, term


class TestUpdateSettings:
    def test_stores_only_what_changed_and_audits_it(self, fakes):
        fakes.store.settings.set_many({"photo_max_mb": 2, "faculty_name_en": "Dentistry"})

        result = fakes.update_settings().execute(
            ADMIN, {"photo_max_mb": 2, "faculty_name_en": "Faculty of Dentistry"}
        )

        assert result["faculty_name_en"] == "Faculty of Dentistry"
        entry = fakes.audit.entries[-1]
        assert (entry.action, entry.model) == ("update", "setup.SystemSetting")
        assert entry.changes == {
            "faculty_name_en": {"old": "Dentistry", "new": "Faculty of Dentistry"}
        }

    def test_settings_sent_to_the_app_change_the_lookups_version(self, fakes):
        service = fakes.update_settings()
        version = fakes.store.settings.lookups_version()

        service.execute(ADMIN, {"faculty_name_en": "Dentistry"})
        assert fakes.store.settings.lookups_version() == version
        service.execute(ADMIN, {"photo_max_mb": 3})

        assert fakes.store.settings.lookups_version() == version + 1

    def test_nothing_changed_writes_nothing(self, fakes):
        fakes.store.settings.set_many({"photo_max_mb": 2})

        fakes.update_settings().execute(ADMIN, {"photo_max_mb": 2})

        assert fakes.audit.entries == []

    def test_a_round_must_end_after_it_starts_with_the_stored_values(self, fakes):
        fakes.store.settings.set_many({"round_morning_start": "08:30"})

        with pytest.raises(DomainError) as error:
            fakes.update_settings().execute(ADMIN, {"round_morning_end": time(8)})

        assert error.value.code == "round_times_invalid"
        assert fakes.store.settings.get("round_morning_end") is None

    def test_the_lookups_version_is_not_a_setting(self, fakes):
        with pytest.raises(DomainError) as error:
            fakes.update_settings().execute(ADMIN, {LOOKUPS_VERSION_KEY: 99})

        assert error.value.code == "setting_unknown"

    @pytest.mark.parametrize("actor", NOT_ADMINS, ids=lambda a: a.role)
    def test_only_the_system_administrator(self, fakes, actor):
        with pytest.raises(AccessDeniedError):
            fakes.update_settings().execute(actor, {"photo_max_mb": 3})


SEED = {
    "settings": {"photo_max_mb": 2, "round_morning_start": "08:30", "round_morning_end": "09:30"},
    "term": [term(start_date="2026-09-14", end_date="2027-01-29")],
    "department": [{"name_ar": "اللبية", "name_en": "Endodontics"}],
    "clinic": [
        {
            "number": "2",
            "name_ar": "عيادة اللبية",
            "name_en": "Endodontics clinic",
            "type": "treatment",
            "department_id@": {"name_en": "Endodontics"},
            "chair_count": 3,
        }
    ],
    "session": [
        {
            "clinic_type": "treatment",
            "name_ar": "الأولى",
            "name_en": "Session 1",
            "start_time": "08:00",
            "end_time": "09:30",
            "order": 1,
        }
    ],
    "case_type": [{"name_ar": "أمامية", "name_en": "Anterior", "kind": "clinical"}],
    "treatment_type": [
        {
            "name_ar": "أمامية",
            "name_en": "Anterior",
            "department_id@": {"name_en": "Endodontics"},
            "case_type_id@": {"name_en": "Anterior"},
        }
    ],
}


def seed(fakes, data=SEED):
    s = fakes.store
    return SeedDefaults(
        s.records, s.terms, s.settings, InMemorySeedSource(data), fakes.audit, fakes.uow
    ).execute()


class TestSeedDefaults:
    def test_creates_the_records_with_their_references(self, fakes):
        report = seed(fakes)

        assert report.created == {
            "term": 1,
            "department": 1,
            "clinic": 1,
            "chair": 3,
            "session": 1,
            "case_type": 1,
            "treatment_type": 1,
            "setting": 3,
        }
        facade = fakes.facade()
        clinic = facade.list_clinics()[0]
        department = facade.list_departments()[0]
        assert clinic.department_id == department.id
        assert [c.number for c in facade.list_chairs(clinic.id)] == [1, 2, 3]
        assert facade.list_sessions(clinic.id)[0].start_time == time(8)
        assert facade.current_term().name == "2026-2027 Fall"
        assert facade.get_setting("photo_max_mb") == 2
        assert all(entry.user_id is None for entry in fakes.audit.entries)

    def test_running_twice_creates_no_duplicates(self, fakes):
        seed(fakes)
        rows_before = {table: len(rows) for table, rows in fakes.store.rows.items()}

        report = seed(fakes)

        assert {table: len(rows) for table, rows in fakes.store.rows.items()} == rows_before
        assert not any(report.created.values())
        assert report.existing["chair"] == 3

    def test_a_deactivated_default_is_not_created_again(self, fakes):
        seed(fakes)
        department_id = fakes.store.records.find(Table.DEPARTMENT, {"name_en": "Endodontics"})
        fakes.store.records.set_active(Table.DEPARTMENT, department_id, False)

        seed(fakes)

        assert len(fakes.store.rows[Table.DEPARTMENT]) == 1

    def test_changed_settings_and_a_newer_current_term_are_kept(self, fakes):
        fakes.store.settings.set_many({"photo_max_mb": 5})
        spring = fakes.save(Table.TERM, **term(name="Spring"))

        seed(fakes)

        assert fakes.store.settings.get("photo_max_mb") == 5
        assert fakes.store.terms.current().id == spring

    def test_the_default_file_loads(self, fakes):
        s = fakes.store
        report = SeedDefaults(
            s.records, s.terms, s.settings, JsonSeedSource(), fakes.audit, fakes.uow
        ).execute()

        assert report.created["tooth_code"] == 10
        assert report.created["chair"] == 24
        assert report.created["index_definition"] == 12
        assert len(fakes.facade().list_clinics()) == 2
