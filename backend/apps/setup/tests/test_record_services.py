"""SaveRecord, SetRecordActive and Reorder (DB-04, DB-06), with in-memory fakes."""

import pytest

from apps.core.domain.errors import AccessDeniedError, DomainError, NotFoundError
from apps.setup.application.services import (
    ReorderCommand,
    SaveRecordCommand,
    SetRecordActiveCommand,
)
from apps.setup.domain.records import Table

from .helpers import ADMIN, NOT_ADMINS, clinic, department, session, term


def lookups_version(fakes) -> int:
    return fakes.store.settings.lookups_version()


class TestSaveRecord:
    def test_creates_a_record_and_audits_it(self, fakes):
        saved = fakes.save_record().execute(
            ADMIN, SaveRecordCommand(Table.DEPARTMENT, department())
        )

        stored = fakes.store.records.get(Table.DEPARTMENT, saved.id)
        assert stored.values["name_en"] == "Endodontics"
        entry = fakes.audit.entries[-1]
        assert (entry.action, entry.model, entry.object_id) == (
            "create",
            "setup.Department",
            str(saved.id),
        )
        assert entry.changes["name_en"] == {"old": None, "new": "Endodontics"}
        assert fakes.uow.commits == 1

    def test_changes_a_record_and_audits_only_what_changed(self, fakes):
        record_id = fakes.save(Table.DEPARTMENT, **department())

        fakes.save(Table.DEPARTMENT, record_id, **department(name_en="Endo"))

        entry = fakes.audit.entries[-1]
        assert entry.action == "update"
        assert entry.changes == {"name_en": {"old": "Endodontics", "new": "Endo"}}

    def test_saving_without_a_change_writes_nothing(self, fakes):
        record_id = fakes.save(Table.DEPARTMENT, **department())
        version = lookups_version(fakes)

        fakes.save(Table.DEPARTMENT, record_id, **department())

        assert fakes.audit.actions() == ["create"]
        assert lookups_version(fakes) == version

    def test_a_list_change_changes_the_lookups_version(self, fakes):
        version = lookups_version(fakes)

        fakes.save(Table.SESSION, **session())

        assert lookups_version(fakes) == version + 1

    def test_a_clinic_is_not_a_lookup_list(self, fakes):
        version = lookups_version(fakes)

        fakes.save(Table.CLINIC, **clinic())

        assert lookups_version(fakes) == version

    @pytest.mark.parametrize("actor", NOT_ADMINS, ids=lambda a: a.role)
    def test_only_the_system_administrator(self, fakes, actor):
        with pytest.raises(AccessDeniedError) as error:
            fakes.save_record().execute(actor, SaveRecordCommand(Table.DEPARTMENT, department()))

        assert error.value.code == "permission_denied"
        assert fakes.store.records.find(Table.DEPARTMENT, {}) is None

    def test_invalid_values_are_refused(self, fakes):
        with pytest.raises(DomainError) as error:
            fakes.save(Table.DEPARTMENT, **department(name_ar=""))

        assert (error.value.code, error.value.details["field"]) == ("value_required", "name_ar")

    def test_a_missing_or_deactivated_record_is_not_found(self, fakes):
        record_id = fakes.save(Table.DEPARTMENT, **department())
        fakes.store.records.set_active(Table.DEPARTMENT, record_id, False)

        for missing in (record_id, 999):
            with pytest.raises(NotFoundError):
                fakes.save(Table.DEPARTMENT, missing, **department())

    def test_clinic_number_is_unique_even_against_deactivated_clinics(self, fakes):
        first = fakes.save(Table.CLINIC, **clinic(number="5"))
        fakes.store.records.set_active(Table.CLINIC, first, False)

        with pytest.raises(DomainError) as error:
            fakes.save(Table.CLINIC, **clinic(number="5", name_en="Another"))

        assert (error.value.code, error.value.details["field"]) == (
            "clinic_number_taken",
            "number",
        )

    def test_a_record_keeps_its_own_unique_value(self, fakes):
        record_id = fakes.save(Table.CLINIC, **clinic(number="5"))

        fakes.save(Table.CLINIC, record_id, **clinic(number="5", building="B"))

        assert fakes.store.records.get(Table.CLINIC, record_id).values["building"] == "B"

    def test_chair_number_is_unique_per_clinic(self, fakes):
        one, two = (
            fakes.save(Table.CLINIC, **clinic()),
            fakes.save(Table.CLINIC, **clinic(number="6")),
        )
        fakes.save(Table.CHAIR, clinic_id=one, number=1)
        fakes.save(Table.CHAIR, clinic_id=two, number=1)  # another clinic: allowed

        with pytest.raises(DomainError) as error:
            fakes.save(Table.CHAIR, clinic_id=one, number=1)

        assert error.value.code == "chair_number_taken"

    def test_tooth_code_letter_is_unique(self, fakes):
        values = {"letter": "D", "meaning_ar": "نخر", "meaning_en": "Decayed", "color": "#d32f2f"}
        fakes.save(Table.TOOTH_CODE, **values)

        with pytest.raises(DomainError) as error:
            fakes.save(Table.TOOTH_CODE, **{**values, "letter": "d"})

        assert error.value.code == "tooth_code_taken"

    def test_index_definition_is_unique_per_index_tooth_and_surface(self, fakes):
        values = {"kind": "plaque", "tooth": 16, "surface": "buccal", "max_score": 3}
        fakes.save(Table.INDEX_DEFINITION, **values)
        fakes.save(Table.INDEX_DEFINITION, **{**values, "kind": "calculus"})

        with pytest.raises(DomainError) as error:
            fakes.save(Table.INDEX_DEFINITION, **values)

        assert error.value.code == "index_definition_taken"

    def test_making_a_term_current_ends_the_previous_current_term(self, fakes):
        first = fakes.save(Table.TERM, **term(name="Fall"))
        second = fakes.save(Table.TERM, **term(name="Spring"))

        assert fakes.store.terms.current().id == second
        assert fakes.store.records.get(Table.TERM, first).values["is_current"] is False

    @pytest.mark.parametrize(
        ("table", "values", "code"),
        [
            (Table.CLINIC, clinic(department_id=999), "department_not_found"),
            (Table.CHAIR, {"clinic_id": 999, "number": 1}, "clinic_not_found"),
            (Table.SESSION, session(clinic_type=None, clinic_id=999), "clinic_not_found"),
        ],
    )
    def test_references_must_be_active_records(self, fakes, table, values, code):
        with pytest.raises(DomainError) as error:
            fakes.save(table, **values)

        assert error.value.code == code

    def test_a_deactivated_department_cannot_be_chosen(self, fakes):
        department_id = fakes.save(Table.DEPARTMENT, **department())
        case_type_id = fakes.save(
            Table.CASE_TYPE, name_ar="أمامية", name_en="Anterior", kind="clinical"
        )
        fakes.store.records.set_active(Table.DEPARTMENT, department_id, False)

        with pytest.raises(DomainError) as error:
            fakes.save(
                Table.TREATMENT_TYPE,
                name_ar="أمامية",
                name_en="Anterior",
                department_id=department_id,
                case_type_id=case_type_id,
            )

        assert (error.value.code, error.value.details["field"]) == (
            "department_not_found",
            "department_id",
        )

    def test_a_chair_stays_in_its_clinic(self, fakes):
        one, two = (
            fakes.save(Table.CLINIC, **clinic()),
            fakes.save(Table.CLINIC, **clinic(number="6")),
        )
        chair = fakes.save(Table.CHAIR, clinic_id=one, number=1)

        fakes.save(Table.CHAIR, chair, clinic_id=two, number=4)

        assert fakes.store.records.get(Table.CHAIR, chair).values == {"clinic_id": one, "number": 4}


class TestSetRecordActive:
    def test_deactivates_and_activates_again(self, fakes):
        record_id = fakes.save(Table.CHECKLIST_ITEM, name_ar="النظافة", name_en="Cleanliness")
        version = lookups_version(fakes)
        service = fakes.set_record_active()

        service.execute(ADMIN, SetRecordActiveCommand(Table.CHECKLIST_ITEM, record_id, False))
        assert not fakes.store.records.is_active(Table.CHECKLIST_ITEM, record_id)
        service.execute(ADMIN, SetRecordActiveCommand(Table.CHECKLIST_ITEM, record_id, True))

        assert fakes.store.records.is_active(Table.CHECKLIST_ITEM, record_id)
        assert fakes.audit.actions()[-2:] == ["deactivate", "activate"]
        assert fakes.audit.entries[-2].changes == {"is_active": {"old": True, "new": False}}
        assert lookups_version(fakes) == version + 2

    def test_the_same_state_again_changes_nothing(self, fakes):
        record_id = fakes.save(Table.CLINIC, **clinic())

        fakes.set_record_active().execute(
            ADMIN, SetRecordActiveCommand(Table.CLINIC, record_id, True)
        )

        assert fakes.audit.actions() == ["create"]

    def test_the_current_term_cannot_be_deactivated(self, fakes):
        record_id = fakes.save(Table.TERM, **term())

        with pytest.raises(DomainError) as error:
            fakes.set_record_active().execute(
                ADMIN, SetRecordActiveCommand(Table.TERM, record_id, False)
            )

        assert error.value.code == "term_is_current"

    def test_a_missing_record_is_not_found(self, fakes):
        with pytest.raises(NotFoundError):
            fakes.set_record_active().execute(
                ADMIN, SetRecordActiveCommand(Table.CLINIC, 999, False)
            )

    @pytest.mark.parametrize("actor", NOT_ADMINS, ids=lambda a: a.role)
    def test_only_the_system_administrator(self, fakes, actor):
        record_id = fakes.save(Table.CLINIC, **clinic())

        with pytest.raises(AccessDeniedError):
            fakes.set_record_active().execute(
                actor, SetRecordActiveCommand(Table.CLINIC, record_id, False)
            )


class TestReorder:
    def sites(self, fakes):
        return [
            fakes.save(Table.SOFT_TISSUE_SITE, name_ar=n, name_en=n, order=i)
            for i, n in enumerate(("Lips", "Tongue", "Palate"), start=1)
        ]

    def test_stores_the_new_order(self, fakes):
        lips, tongue, palate = self.sites(fakes)

        fakes.reorder().execute(
            ADMIN, ReorderCommand(Table.SOFT_TISSUE_SITE, {palate: 1, lips: 2, tongue: 3})
        )

        names = [s.name_en for s in fakes.store.lookups.lookup_lists().soft_tissue_sites]
        assert names == ["Palate", "Lips", "Tongue"]

    def test_only_lists_have_an_order(self, fakes):
        with pytest.raises(NotFoundError):
            fakes.reorder().execute(ADMIN, ReorderCommand(Table.CLINIC, {}))

    def test_a_missing_item_is_not_found(self, fakes):
        with pytest.raises(NotFoundError):
            fakes.reorder().execute(ADMIN, ReorderCommand(Table.SOFT_TISSUE_SITE, {999: 1}))

    def test_only_the_system_administrator(self, fakes):
        lips, *_ = self.sites(fakes)

        with pytest.raises(AccessDeniedError):
            fakes.reorder().execute(
                NOT_ADMINS[0], ReorderCommand(Table.SOFT_TISSUE_SITE, {lips: 9})
            )
