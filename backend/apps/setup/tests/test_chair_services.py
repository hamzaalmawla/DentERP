"""AddChairs and SetChairStatus (DB-04, MT-07, BR-12), with in-memory fakes."""

import pytest

from apps.core.domain.errors import AccessDeniedError, DomainError, NotFoundError
from apps.setup.application.dtos import ChairStatus, SetChairStatusCommand
from apps.setup.application.services import AddChairsCommand
from apps.setup.domain.records import Table

from .helpers import ADMIN, NOT_ADMINS, clinic


@pytest.fixture
def clinic_id(fakes) -> int:
    return fakes.save(Table.CLINIC, **clinic())


class TestAddChairs:
    def test_adds_chairs_in_service_numbered_from_one(self, fakes, clinic_id):
        saved = fakes.add_chairs().execute(ADMIN, AddChairsCommand(clinic_id, 12))

        chairs = fakes.store.chairs.list_for_clinic([clinic_id], in_service_only=True)
        assert [c.number for c in chairs] == list(range(1, 13))
        assert [s.id for s in saved] == [c.id for c in chairs]
        assert fakes.audit.actions().count("create") == 13  # the clinic and 12 chairs

    def test_numbers_continue_after_the_highest_chair_even_a_deactivated_one(
        self, fakes, clinic_id
    ):
        last = fakes.save(Table.CHAIR, clinic_id=clinic_id, number=7)
        fakes.store.records.set_active(Table.CHAIR, last, False)

        fakes.add_chairs().execute(ADMIN, AddChairsCommand(clinic_id, 2))

        chairs = fakes.store.chairs.list_for_clinic([clinic_id], in_service_only=False)
        assert [c.number for c in chairs] == [8, 9]

    @pytest.mark.parametrize("count", [0, 101, -1, True])
    def test_count_from_1_to_100(self, fakes, clinic_id, count):
        with pytest.raises(DomainError) as error:
            fakes.add_chairs().execute(ADMIN, AddChairsCommand(clinic_id, count))

        assert error.value.code == "chair_count_invalid"

    def test_the_clinic_must_be_active(self, fakes, clinic_id):
        fakes.store.records.set_active(Table.CLINIC, clinic_id, False)

        with pytest.raises(DomainError) as error:
            fakes.add_chairs().execute(ADMIN, AddChairsCommand(clinic_id, 1))

        assert error.value.code == "clinic_not_found"

    @pytest.mark.parametrize("actor", NOT_ADMINS, ids=lambda a: a.role)
    def test_only_the_system_administrator(self, fakes, clinic_id, actor):
        with pytest.raises(AccessDeniedError):
            fakes.add_chairs().execute(actor, AddChairsCommand(clinic_id, 1))


class TestSetChairStatus:
    @pytest.fixture
    def chair_id(self, fakes, clinic_id) -> int:
        return fakes.save(Table.CHAIR, clinic_id=clinic_id, number=1)

    def command(self, chair_id, status=ChairStatus.OUT_OF_SERVICE, reason="Broken light", by=7):
        return SetChairStatusCommand(chair_id, status, reason, by)

    def test_takes_the_chair_out_of_service_and_writes_history(self, fakes, chair_id):
        chair = fakes.set_chair_status().execute(self.command(chair_id))

        assert chair.status == ChairStatus.OUT_OF_SERVICE
        ((at, change),) = fakes.store.history
        assert at == fakes.clock.now()
        assert (change.from_status, change.to_status, change.reason, change.by_user_id) == (
            ChairStatus.IN_SERVICE,
            ChairStatus.OUT_OF_SERVICE,
            "Broken light",
            7,
        )
        entry = fakes.audit.entries[-1]
        assert (entry.action, entry.user_id) == ("chair_status", 7)
        assert entry.changes["reason"] == "Broken light"

    def test_an_out_of_service_chair_is_not_given_to_students(self, fakes, clinic_id, chair_id):
        fakes.set_chair_status().execute(self.command(chair_id))

        assert fakes.store.chairs.list_for_clinic([clinic_id], in_service_only=True) == []

    def test_the_system_can_do_it(self, fakes, chair_id):
        fakes.set_chair_status().execute(self.command(chair_id, by=None))

        assert fakes.store.history[-1][1].by_user_id is None

    @pytest.mark.parametrize("reason", ["", "   "])
    def test_a_reason_is_required(self, fakes, chair_id, reason):
        with pytest.raises(DomainError) as error:
            fakes.set_chair_status().execute(self.command(chair_id, reason=reason))

        assert (error.value.code, error.value.details["field"]) == ("reason_required", "reason")
        assert fakes.store.history == []

    def test_the_same_status_changes_nothing(self, fakes, chair_id):
        fakes.set_chair_status().execute(self.command(chair_id, status=ChairStatus.IN_SERVICE))

        assert fakes.store.history == []
        assert "chair_status" not in fakes.audit.actions()

    def test_back_in_service(self, fakes, chair_id):
        service = fakes.set_chair_status()
        service.execute(self.command(chair_id))

        chair = service.execute(
            self.command(chair_id, status=ChairStatus.IN_SERVICE, reason="Fixed")
        )

        assert chair.in_service
        assert [c.to_status for _at, c in fakes.store.history] == [
            ChairStatus.OUT_OF_SERVICE,
            ChairStatus.IN_SERVICE,
        ]

    def test_a_deactivated_chair_is_not_found(self, fakes, chair_id):
        fakes.store.records.set_active(Table.CHAIR, chair_id, False)

        with pytest.raises(NotFoundError):
            fakes.set_chair_status().execute(self.command(chair_id))
