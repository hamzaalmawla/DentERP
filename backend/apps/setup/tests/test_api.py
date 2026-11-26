"""GET /api/v1/lookups/ and GET /api/v1/clinics/ (design section 7, SYS-07)."""

from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.domain.roles import RoleCode
from apps.setup import container
from apps.setup.application.dtos import ChairStatus
from apps.setup.application.services import SaveRecordCommand
from apps.setup.domain.records import Table
from apps.setup.models import Chair, Clinic, MedicalHistoryItem

from .helpers import ADMIN

pytestmark = pytest.mark.django_db

LOOKUPS = "/api/v1/lookups/"
CLINICS = "/api/v1/clinics/"


@pytest.fixture
def seeded():
    call_command("seed_defaults", stdout=StringIO())


class TestLookups:
    @pytest.mark.parametrize("role", list(RoleCode))
    def test_every_role_gets_the_lists(self, api, seeded, role):
        response = api(role).get(LOOKUPS)

        assert response.status_code == 200
        body = response.json()
        assert {
            "version",
            "departments",
            "case_types",
            "treatment_types",
            "tooth_codes",
            "medical_history_items",
            "soft_tissue_sites",
            "index_definitions",
            "checklist_items",
            "fault_categories",
            "sessions",
            "settings",
        } <= body.keys()

    def test_anonymous_callers_are_refused(self):
        assert APIClient().get(LOOKUPS).status_code == 401

    def test_names_in_english(self, api, seeded):
        body = api("student", language="en").get(LOOKUPS).json()

        assert [t["letter"] for t in body["tooth_codes"]][:3] == ["D", "M", "F"]
        assert body["tooth_codes"][0] == {
            "id": body["tooth_codes"][0]["id"],
            "letter": "D",
            "meaning": "Decayed",
            "color": "#d32f2f",
        }
        assert body["checklist_items"][0]["name"] == "Cleanliness"
        assert body["sessions"][0]["start_time"] == "08:00"
        assert body["settings"]["photo_max_mb"] == 2
        assert body["settings"]["round_morning_start"] == "08:30"

    def test_names_in_arabic(self, api, seeded):
        body = api("student", language="ar").get(LOOKUPS).json()

        assert body["tooth_codes"][0]["meaning"] == "نخر"
        assert body["checklist_items"][0]["name"] == "النظافة"
        alert = next(i for i in body["medical_history_items"] if i["is_alert"])
        assert alert["question"] == MedicalHistoryItem.objects.get(pk=alert["id"]).question_ar

    def test_the_etag_returns_304_until_a_list_changes(self, api, seeded):
        client = api("student")
        first = client.get(LOOKUPS)
        etag = first["ETag"]
        assert etag == f'"lookups-{first.json()["version"]}-en"'

        unchanged = client.get(LOOKUPS, HTTP_IF_NONE_MATCH=etag)
        assert unchanged.status_code == 304
        assert unchanged["ETag"] == etag
        assert not unchanged.content

        item = MedicalHistoryItem.objects.first()
        container.save_record().execute(ADMIN, save_command(item, question_en="Heart (any)"))

        changed = client.get(LOOKUPS, HTTP_IF_NONE_MATCH=etag)
        assert changed.status_code == 200
        assert changed.json()["version"] > first.json()["version"]
        assert changed["ETag"] != etag

    def test_the_etag_differs_by_language(self, api, seeded):
        english = api("student", language="en").get(LOOKUPS)
        arabic = api("supervisor", language="ar").get(LOOKUPS, HTTP_IF_NONE_MATCH=english["ETag"])

        assert arabic.status_code == 200
        assert "Accept-Language" in arabic["Vary"]

    def test_deactivated_items_are_left_out(self, api, seeded):
        item = MedicalHistoryItem.objects.first()
        item.deactivate()

        body = api("student").get(LOOKUPS).json()

        assert item.pk not in [i["id"] for i in body["medical_history_items"]]


def save_command(item, **changes) -> SaveRecordCommand:
    values = {
        "question_ar": item.question_ar,
        "question_en": item.question_en,
        "answer_type": item.answer_type,
        "is_alert": item.is_alert,
        "order": item.order,
        **changes,
    }
    return SaveRecordCommand(Table.MEDICAL_HISTORY_ITEM, values, item.pk)


class TestClinics:
    @pytest.mark.parametrize("role", list(RoleCode))
    def test_every_role_gets_the_clinics(self, api, seeded, role):
        response = api(role).get(CLINICS)

        assert response.status_code == 200
        assert [c["number"] for c in response.json()] == ["1", "2"]

    def test_anonymous_callers_are_refused(self):
        assert APIClient().get(CLINICS).status_code == 401

    def test_filter_by_type_with_names_in_the_request_language(self, api, seeded):
        body = api("supervisor", language="ar").get(CLINICS, {"type": "treatment"}).json()

        assert len(body) == 1
        assert body[0]["name"] == "عيادة المداواة اللبية"
        assert body[0]["type"] == "treatment"
        assert "chairs" not in body[0]

    def test_an_unknown_type_is_a_validation_error(self, api):
        response = api("technician").get(CLINICS, {"type": "surgery"})

        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_with_chair_status(self, api, seeded):
        endo = Clinic.objects.get(type="treatment")
        broken = Chair.objects.get(clinic=endo, number=3)
        container.facade().set_chair_status(
            broken.pk, ChairStatus.OUT_OF_SERVICE, reason="Leak", by_user_id=None
        )
        Chair.objects.get(clinic=endo, number=12).deactivate()

        body = api("technician").get(CLINICS, {"type": "treatment", "with": "chair_status"})

        clinic = body.json()[0]
        assert (clinic["chairs_in_service"], clinic["chairs_out_of_service"]) == (10, 1)
        assert len(clinic["chairs"]) == 11
        assert {"id": broken.pk, "number": 3, "status": "out_of_service"} in clinic["chairs"]

    def test_deactivated_clinics_are_left_out(self, api, seeded):
        Clinic.objects.get(number="1").deactivate()

        assert [c["number"] for c in api("student").get(CLINICS).json()] == ["2"]
