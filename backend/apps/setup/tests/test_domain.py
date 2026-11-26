"""The rules of the configuration records and the system settings (plain Python)."""

from datetime import date, time

import pytest

from apps.setup.domain.errors import InvalidValueError
from apps.setup.domain.records import Table, clean, is_fdi_permanent_tooth
from apps.setup.domain.settings import check_windows, clean_settings

from .helpers import clinic, department, session, term


def refused(table: Table, values: dict) -> InvalidValueError:
    with pytest.raises(InvalidValueError) as error:
        clean(table, values)
    return error.value


class TestRecords:
    def test_text_is_stripped_and_unknown_values_ignored(self):
        values = clean(Table.DEPARTMENT, department(name_ar="  اللبية ", extra="x"))

        assert values == {"name_ar": "اللبية", "name_en": "Endodontics", "head_id": None}

    @pytest.mark.parametrize("field", ["name_ar", "name_en"])
    def test_both_names_are_required(self, field):
        error = refused(Table.DEPARTMENT, department(**{field: "  "}))

        assert (error.code, error.details["field"]) == ("value_required", field)

    def test_too_long(self):
        error = refused(Table.CLINIC, clinic(number="12345678901"))

        assert (error.code, error.details) == ("too_long", {"field": "number", "max": 10})

    def test_clinic_type_must_be_known(self):
        error = refused(Table.CLINIC, clinic(type="surgery"))

        assert (error.code, error.details["field"]) == ("choice_invalid", "type")

    def test_term_ends_after_it_starts(self):
        error = refused(Table.TERM, term(end_date=date(2026, 9, 14)))

        assert (error.code, error.details["field"]) == ("term_dates_invalid", "end_date")

    @pytest.mark.parametrize(
        "values",
        [
            {"clinic_type": None},  # neither
            {"clinic_id": 3},  # both
        ],
    )
    def test_session_for_a_clinic_or_a_type(self, values):
        error = refused(Table.SESSION, session(**values))

        assert error.code == "session_target_required"

    def test_session_ends_after_it_starts(self):
        error = refused(Table.SESSION, session(end_time=time(8)))

        assert (error.code, error.details["field"]) == ("session_times_invalid", "end_time")

    def test_session_of_one_clinic(self):
        values = clean(Table.SESSION, session(clinic_type="", clinic_id=3))

        assert (values["clinic_id"], values["clinic_type"]) == (3, None)

    def test_tooth_code_letter_is_one_latin_letter_in_upper_case(self):
        values = clean(
            Table.TOOTH_CODE,
            {"letter": "d", "meaning_ar": "نخر", "meaning_en": "Decayed", "color": "#D32F2F"},
        )

        assert (values["letter"], values["color"]) == ("D", "#d32f2f")
        assert refused(Table.TOOTH_CODE, {**values, "letter": "ن"}).code == (
            "tooth_code_letter_invalid"
        )
        assert refused(Table.TOOTH_CODE, {**values, "color": "red"}).code == "color_invalid"

    @pytest.mark.parametrize(("tooth", "valid"), [(11, True), (48, True), (19, False), (51, False)])
    def test_fdi_permanent_teeth(self, tooth, valid):
        assert is_fdi_permanent_tooth(tooth) is valid

    def test_index_definition(self):
        values = {"kind": "plaque", "tooth": 16, "surface": "buccal", "min_score": 0}

        assert clean(Table.INDEX_DEFINITION, {**values, "max_score": 3})["tooth"] == 16
        assert refused(Table.INDEX_DEFINITION, {**values, "tooth": 19, "max_score": 3}).code == (
            "tooth_invalid"
        )
        assert refused(Table.INDEX_DEFINITION, {**values, "max_score": 0}).code == (
            "score_range_invalid"
        )

    @pytest.mark.parametrize("order", [-1, 1.5, True, "2"])
    def test_order_is_a_whole_number(self, order):
        values = {"name_ar": "النظافة", "name_en": "Cleanliness", "order": order}

        assert refused(Table.CHECKLIST_ITEM, values).code == "number_invalid"

    def test_chair_number_is_positive(self):
        assert refused(Table.CHAIR, {"clinic_id": 1, "number": 0}).code == "number_invalid"

    def test_treatment_type_needs_a_department_and_a_case_type(self):
        error = refused(
            Table.TREATMENT_TYPE, {"name_ar": "لبية", "name_en": "RCT", "case_type_id": 2}
        )

        assert (error.code, error.details["field"]) == ("value_required", "department_id")


class TestSettings:
    def test_cleaned_into_their_stored_form(self):
        cleaned = clean_settings(
            {
                "university_name_en": " SPU ",
                "photo_max_mb": 4,
                "push_notifications_enabled": 0,
                "round_morning_start": time(8, 30),
            }
        )

        assert cleaned == {
            "university_name_en": "SPU",
            "photo_max_mb": 4,
            "push_notifications_enabled": False,
            "round_morning_start": "08:30",
        }

    @pytest.mark.parametrize(
        ("values", "code"),
        [
            ({"nope": 1}, "setting_unknown"),
            ({"photo_max_mb": 0}, "number_invalid"),
            ({"photo_max_mb": 21}, "number_invalid"),
            ({"default_language": "fr"}, "choice_invalid"),
            ({"faculty_name_ar": ""}, "value_required"),
            ({"round_morning_end": None}, "value_required"),
        ],
    )
    def test_refused(self, values, code):
        with pytest.raises(InvalidValueError) as error:
            clean_settings(values)

        assert error.value.code == code
        assert error.value.details["field"] == next(iter(values))

    def test_a_round_ends_after_it_starts(self):
        with pytest.raises(InvalidValueError) as error:
            check_windows({"round_afternoon_start": "15:00", "round_afternoon_end": "14:00"})

        assert (error.value.code, error.value.details["field"]) == (
            "round_times_invalid",
            "round_afternoon_end",
        )
