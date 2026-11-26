"""The ORM adapters against PostgreSQL, the database constraints, and seed_defaults."""

from datetime import UTC, date, datetime, time
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction

from apps.core.models import AuditLog
from apps.setup import container
from apps.setup.application.dtos import ChairStatus, ClinicType
from apps.setup.domain.records import Table
from apps.setup.infrastructure.repositories import (
    OrmChairRepository,
    OrmClinicRepository,
    OrmLookupRepository,
    OrmRecordRepository,
    OrmSettingRepository,
    OrmTermRepository,
)
from apps.setup.models import (
    CaseType,
    Chair,
    ChairStatusChange,
    Clinic,
    Department,
    IndexDefinition,
    Session,
    SystemSetting,
    Term,
    ToothCode,
    TreatmentType,
)

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)


def make_clinic(number="5", **values) -> Clinic:
    return Clinic.objects.create(
        number=number, name_ar="عيادة", name_en="Clinic", type="treatment", **values
    )


def refused(model, values: dict) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(**values)


class TestConstraints:
    def test_clinic_number_is_unique(self):
        make_clinic("5")
        refused(Clinic, {"number": "5", "name_ar": "x", "name_en": "x", "type": "lab"})

    def test_chair_number_is_unique_per_clinic(self):
        one, two = make_clinic("1"), make_clinic("2")
        Chair.objects.create(clinic=one, number=1)
        Chair.objects.create(clinic=two, number=1)
        refused(Chair, {"clinic": one, "number": 1})

    def test_tooth_code_letter_is_unique(self):
        ToothCode.objects.create(letter="D", meaning_ar="x", meaning_en="x", color="#000000")
        refused(ToothCode, {"letter": "D", "meaning_ar": "y", "meaning_en": "y"})

    def test_one_current_term(self):
        values = {"start_date": date(2026, 9, 1), "end_date": date(2027, 1, 31)}
        Term.objects.create(name="Fall", is_current=True, **values)
        Term.objects.create(name="Old", is_current=False, **values)
        refused(Term, {"name": "Spring", "is_current": True, **values})

    def test_term_ends_after_it_starts(self):
        day = date(2026, 9, 1)
        refused(Term, {"name": "x", "start_date": day, "end_date": day})

    def test_session_belongs_to_a_clinic_or_a_type(self):
        times = {"name_ar": "x", "name_en": "x", "start_time": time(8), "end_time": time(9)}
        refused(Session, times)
        refused(Session, {**times, "clinic": make_clinic(), "clinic_type": "lab"})

    def test_index_definition_is_unique_and_its_range_is_valid(self):
        values = {"kind": "plaque", "tooth": 16, "surface": "buccal"}
        IndexDefinition.objects.create(**values)
        refused(IndexDefinition, values)
        refused(IndexDefinition, {**values, "tooth": 11, "max_score": 0})

    def test_records_are_never_deleted(self):
        clinic = make_clinic()
        with pytest.raises(Exception, match="cannot be deleted"):
            clinic.delete()


class TestRecordRepository:
    def test_create_get_update_find_and_deactivate(self):
        records = OrmRecordRepository()
        department_id = records.create(Table.DEPARTMENT, {"name_ar": "أ", "name_en": "A"})
        clinic_id = records.create(
            Table.CLINIC,
            {
                "number": "5",
                "name_ar": "ع",
                "name_en": "C",
                "type": ClinicType.TREATMENT,
                "department_id": department_id,
                "building": "",
                "floor": "",
            },
        )

        records.update(Table.CLINIC, clinic_id, {"department_id": None, "floor": "2"})
        records.set_active(Table.CLINIC, clinic_id, False)

        stored = records.get(Table.CLINIC, clinic_id)
        assert stored.values["department_id"] is None
        assert (stored.values["floor"], stored.values["type"], stored.is_active) == (
            "2",
            "treatment",
            False,
        )
        assert not records.is_active(Table.CLINIC, clinic_id)
        assert records.find(Table.CLINIC, {"number": "5"}) == clinic_id  # deactivated too
        assert records.find(Table.CLINIC, {"number": "5"}, exclude_id=clinic_id) is None
        assert records.get(Table.CLINIC, 999) is None


class TestChairRepository:
    def test_status_history_and_numbers(self, make_user):
        user = make_user("tech", "technician")
        clinic = make_clinic()
        one = Chair.objects.create(clinic=clinic, number=1)
        two = Chair.objects.create(clinic=clinic, number=2)
        Chair.objects.create(clinic=clinic, number=9, is_active=False)
        chairs = OrmChairRepository()

        changed = chairs.set_status(
            one.pk, ChairStatus.OUT_OF_SERVICE, reason="Leak", by_user_id=user.pk, at=NOW
        )

        assert changed.status == ChairStatus.OUT_OF_SERVICE
        row = ChairStatusChange.objects.get()
        assert (row.from_status, row.to_status, row.by_id, row.at) == (
            "in_service",
            "out_of_service",
            user.pk,
            NOW,
        )
        assert [c.id for c in chairs.list_for_clinic([clinic.pk], in_service_only=True)] == [two.pk]
        assert len(chairs.list_for_clinic([clinic.pk], in_service_only=False)) == 2
        assert chairs.next_number(clinic.pk) == 10
        one.deactivate()
        assert chairs.get(one.pk) is None
        assert [h.reason for h in chairs.history(one.pk)] == ["Leak"]


class TestReadRepositories:
    def test_clinics_by_number(self):
        ten, two = make_clinic("10"), make_clinic("2", is_active=True)
        make_clinic("3", is_active=False)

        assert [c.id for c in OrmClinicRepository().list()] == [two.pk, ten.pk]
        assert OrmClinicRepository().list(type=ClinicType.LAB) == []

    def test_sessions_of_the_clinic_or_else_of_its_type(self):
        own, other = make_clinic("1"), make_clinic("2")
        times = {"name_ar": "x", "name_en": "x", "start_time": time(8), "end_time": time(9)}
        typed = Session.objects.create(clinic_type="treatment", **times)
        mine = Session.objects.create(clinic=own, **times)
        lookups, clinics = OrmLookupRepository(), OrmClinicRepository()

        assert [s.id for s in lookups.sessions_for(clinics.get(own.pk))] == [mine.pk]
        assert [s.id for s in lookups.sessions_for(clinics.get(other.pk))] == [typed.pk]

    def test_lookup_lists_leave_out_deactivated_rows(self):
        department = Department.objects.create(name_ar="أ", name_en="A")
        ToothCode.objects.create(letter="D", meaning_ar="x", meaning_en="x", color="#000", order=2)
        ToothCode.objects.create(letter="M", meaning_ar="x", meaning_en="x", color="#000", order=1)
        ToothCode.objects.create(
            letter="Z", meaning_ar="x", meaning_en="x", color="#000", is_active=False
        )
        gone = make_clinic("9", is_active=False)
        Session.objects.create(
            clinic=gone, name_ar="x", name_en="x", start_time=time(8), end_time=time(9)
        )

        lists = OrmLookupRepository().lookup_lists()

        assert [t.letter for t in lists.tooth_codes] == ["M", "D"]
        assert [d.id for d in lists.departments] == [department.pk]
        assert lists.sessions == ()

    def test_treatment_types_of_a_deactivated_department_are_left_out(self):
        department = Department.objects.create(name_ar="أ", name_en="A", is_active=False)
        case_type = CaseType.objects.create(name_ar="x", name_en="x", kind="clinical")
        TreatmentType.objects.create(
            name_ar="x", name_en="x", department=department, case_type=case_type
        )

        assert OrmLookupRepository().lookup_lists().treatment_types == ()

    def test_term_and_settings(self):
        values = {"start_date": date(2026, 9, 1), "end_date": date(2027, 1, 31)}
        old = Term.objects.create(name="Fall", is_current=True, **values)
        new = Term.objects.create(name="Spring", **values)
        terms, settings = OrmTermRepository(), OrmSettingRepository()

        terms.clear_current(except_id=new.pk)
        Term.objects.filter(pk=new.pk).update(is_current=True)
        settings.set_many({"photo_max_mb": 3})
        settings.set_many({"photo_max_mb": 4})

        old.refresh_from_db()
        assert old.is_current is False
        assert terms.current().id == new.pk
        assert settings.get("photo_max_mb") == 4
        assert settings.lookups_version() == 1
        assert settings.bump_lookups_version() == 2
        assert settings.bump_lookups_version() == 3
        assert SystemSetting.objects.count() == 2


class TestSeedDefaultsCommand:
    def test_seed_defaults_run_twice_creates_no_duplicates(self):
        call_command("seed_defaults", stdout=StringIO())
        counts = {
            model.__name__: model.all_objects.count()
            for model in (Department, Clinic, Chair, Session, ToothCode, TreatmentType)
        }
        version = OrmSettingRepository().lookups_version()

        call_command("seed_defaults", stdout=StringIO())

        assert counts == {
            "Department": 2,
            "Clinic": 2,
            "Chair": 24,
            "Session": 10,
            "ToothCode": 10,
            "TreatmentType": 4,
        }
        assert counts == {
            model.__name__: model.all_objects.count()
            for model in (Department, Clinic, Chair, Session, ToothCode, TreatmentType)
        }
        assert OrmSettingRepository().lookups_version() == version
        assert AuditLog.objects.filter(model="setup.Clinic", action="create").count() == 2

    def test_tests_start_without_seed_data(self):
        assert not Clinic.all_objects.exists()
        assert not SystemSetting.all_objects.exists()

    def test_the_facade_over_the_seeded_database(self):
        call_command("seed_defaults", stdout=StringIO())
        facade = container.facade()

        endo = facade.list_clinics(type=ClinicType.TREATMENT)[0]
        assert len(facade.list_chairs(endo.id, in_service_only=True)) == 12
        assert len(facade.list_sessions(endo.id)) == 5
        assert facade.current_term().is_current
        assert len(facade.list_checklist_items()) == 4
        assert facade.get_setting("round_morning_start") == "08:30"
        lookups = container.get_lookups().execute()
        assert len(lookups.medical_history_items) == 19
        assert len(lookups.index_definitions) == 12
