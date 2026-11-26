"""The setup facade (docs/contracts.md) and the US-01 acceptance criteria, with in-memory
fakes. The same facade over the database is checked in test_repositories.py."""

from datetime import time

import pytest

from apps.core.domain.errors import DomainError, NotFoundError
from apps.setup.application.dtos import ChairStatus, ClinicType
from apps.setup.application.services import AddChairsCommand, SetRecordActiveCommand
from apps.setup.domain.records import Table

from .helpers import ADMIN, clinic, department, session, term


@pytest.fixture
def facade(fakes):
    return fakes.facade()


class TestUS01:
    """US-01: create clinic 5 (treatment, 12 chairs) and 5 sessions; the chairs appear in
    distribution and rounds; deactivating a chair hides it from new distributions but keeps
    its history."""

    @pytest.fixture
    def clinic_5(self, fakes):
        clinic_id = fakes.save(Table.CLINIC, **clinic(number="5"))
        fakes.add_chairs().execute(ADMIN, AddChairsCommand(clinic_id, 12))
        for order, start in enumerate((8, 10, 12, 14, 16), start=1):
            fakes.save(
                Table.SESSION,
                **session(
                    clinic_type=None,
                    clinic_id=clinic_id,
                    name_en=f"Session {order}",
                    start_time=time(start),
                    end_time=time(start + 1, 30),
                    order=order,
                ),
            )
        return clinic_id

    def test_us01_create_a_clinic_with_12_chairs_and_5_sessions(self, facade, clinic_5):
        assert facade.get_clinic(clinic_5).type == ClinicType.TREATMENT
        assert len(facade.list_chairs(clinic_5)) == 12
        assert [s.name_en for s in facade.list_sessions(clinic_5)] == [
            f"Session {n}" for n in range(1, 6)
        ]

    def test_us01_the_chairs_appear_in_distribution_and_rounds(self, facade, clinic_5):
        # Distribution reads the chairs in service; rounds read every active chair.
        assert len(facade.list_chairs(clinic_5, in_service_only=True)) == 12
        assert len(facade.list_chairs(clinic_5)) == 12

    def test_us01_deactivating_a_chair_hides_it_but_keeps_its_history(
        self, fakes, facade, clinic_5
    ):
        chair = facade.list_chairs(clinic_5)[0]
        facade.set_chair_status(
            chair.id, ChairStatus.OUT_OF_SERVICE, reason="Broken light", by_user_id=3
        )

        fakes.set_record_active().execute(
            ADMIN, SetRecordActiveCommand(Table.CHAIR, chair.id, False)
        )

        assert chair.id not in [c.id for c in facade.list_chairs(clinic_5, in_service_only=True)]
        assert chair.id not in [c.id for c in facade.list_chairs(clinic_5)]
        assert [h.reason for h in fakes.store.chairs.history(chair.id)] == ["Broken light"]
        with pytest.raises(NotFoundError):
            facade.get_chair(chair.id)


class TestFacade:
    def test_current_term(self, fakes, facade):
        with pytest.raises(NotFoundError):
            facade.current_term()

        term_id = fakes.save(Table.TERM, **term())

        assert facade.current_term().id == term_id

    def test_departments(self, fakes, facade):
        first = fakes.save(Table.DEPARTMENT, **department(name_ar="ب"))
        second = fakes.save(Table.DEPARTMENT, **department(name_ar="أ"))
        fakes.store.records.set_active(Table.DEPARTMENT, first, False)

        assert [d.id for d in facade.list_departments()] == [second]
        assert facade.get_department(second).name_ar == "أ"
        with pytest.raises(NotFoundError):
            facade.get_department(first)

    def test_clinics_by_number_and_type(self, fakes, facade):
        ten = fakes.save(Table.CLINIC, **clinic(number="10"))
        two = fakes.save(Table.CLINIC, **clinic(number="2", type="diagnosis"))
        gone = fakes.save(Table.CLINIC, **clinic(number="3"))
        fakes.store.records.set_active(Table.CLINIC, gone, False)

        assert [c.id for c in facade.list_clinics()] == [two, ten]
        assert [c.id for c in facade.list_clinics(type=ClinicType.DIAGNOSIS)] == [two]
        with pytest.raises(NotFoundError):
            facade.get_clinic(gone)

    def test_sessions_of_the_clinic_or_else_of_its_type(self, fakes, facade):
        own = fakes.save(Table.CLINIC, **clinic(number="1"))
        other = fakes.save(Table.CLINIC, **clinic(number="2"))
        typed = fakes.save(Table.SESSION, **session())
        mine = fakes.save(Table.SESSION, **session(clinic_type=None, clinic_id=own))

        assert [s.id for s in facade.list_sessions(own)] == [mine]
        assert [s.id for s in facade.list_sessions(other)] == [typed]

    def test_set_chair_status_through_the_facade(self, fakes, facade):
        clinic_id = fakes.save(Table.CLINIC, **clinic())
        chair_id = fakes.save(Table.CHAIR, clinic_id=clinic_id, number=1)

        with pytest.raises(DomainError) as error:
            facade.set_chair_status(chair_id, ChairStatus.OUT_OF_SERVICE, reason="", by_user_id=1)
        assert error.value.code == "reason_required"

        chair = facade.set_chair_status(
            chair_id, ChairStatus.OUT_OF_SERVICE, reason="Leak", by_user_id=None
        )
        assert not chair.in_service
        assert facade.get_chair(chair_id) == chair

    def test_lists(self, fakes, facade):
        department_id = fakes.save(Table.DEPARTMENT, **department())
        case_type = fakes.save(Table.CASE_TYPE, name_ar="أمامية", name_en="Anterior", kind="lab")
        treatment = fakes.save(
            Table.TREATMENT_TYPE,
            name_ar="أمامية",
            name_en="Anterior",
            department_id=department_id,
            case_type_id=case_type,
        )
        fault = fakes.save(Table.FAULT_CATEGORY, name_ar="كهرباء", name_en="Power", blocks_chair=1)
        second = fakes.save(Table.CHECKLIST_ITEM, name_ar="ب", name_en="B", order=2)
        first = fakes.save(Table.CHECKLIST_ITEM, name_ar="أ", name_en="A", order=1)

        assert facade.get_case_type(case_type).kind == "lab"
        assert facade.get_treatment_type(treatment).department_id == department_id
        assert facade.get_fault_category(fault).blocks_chair is True
        assert [i.id for i in facade.list_checklist_items()] == [first, second]
        for missing in (facade.get_case_type, facade.get_treatment_type):
            with pytest.raises(NotFoundError):
                missing(999)

    def test_settings_and_version(self, fakes, facade):
        version = facade.get_lookups_version()
        fakes.update_settings().execute(ADMIN, {"photo_max_mb": 4})

        assert facade.get_setting("photo_max_mb") == 4
        assert facade.get_setting("missing", default="x") == "x"
        assert facade.get_lookups_version() == version + 1
