"""Setup screens on the dashboard (DB-04, DB-06, DB-18): only the super admin opens them,
and every change goes through a setup service."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import translation

from apps.core.models import AuditLog
from apps.setup.models import (
    Chair,
    ChairStatusChange,
    Clinic,
    Department,
    Session,
    SoftTissueSite,
    SystemSetting,
    Term,
    ToothCode,
)

pytestmark = pytest.mark.django_db

SCREENS = [
    "/dashboard/setup/department/",
    "/dashboard/setup/department/add/",
    "/dashboard/setup/clinic/",
    "/dashboard/setup/clinic/add/",
    "/dashboard/setup/chair/",
    "/dashboard/setup/session/",
    "/dashboard/setup/term/",
    "/dashboard/setup/casetype/",
    "/dashboard/setup/toothcode/",
    "/dashboard/setup/medicalhistoryitem/",
    "/dashboard/setup/softtissuesite/",
    "/dashboard/setup/indexdefinition/",
    "/dashboard/setup/treatmenttype/",
    "/dashboard/setup/checklistitem/",
    "/dashboard/setup/faultcategory/",
    "/dashboard/setup/systemsetting/",
]


def clinic_data(**values) -> dict:
    return {
        "number": "5",
        "name_ar": "عيادة اللبية",
        "name_en": "Endodontics",
        "type": "treatment",
        "department": "",
        "building": "A",
        "floor": "2",
        "chairs_to_add": "",
        "_save": "1",
        # The chairs table on the page (read-only).
        "chairs-TOTAL_FORMS": "0",
        "chairs-INITIAL_FORMS": "0",
        **values,
    }


def form_errors(response) -> dict:
    return response.context["adminform"].form.errors


@pytest.fixture
def admin_client(dashboard):
    return dashboard("super_admin")


class TestAccess:
    @pytest.mark.parametrize("url", SCREENS)
    def test_the_super_admin_opens_the_setup_screens(self, admin_client, url):
        assert admin_client.get(url).status_code == 200

    @pytest.mark.parametrize("role", ["management", "reception", "supervisor"])
    @pytest.mark.parametrize("url", SCREENS)
    def test_only_the_super_admin_opens_the_setup_screens(self, dashboard, role, url):
        assert dashboard(role).get(url).status_code == 403

    def test_the_sidebar_shows_facilities_lists_and_settings(self, admin_client):
        response = admin_client.get("/dashboard/")

        with translation.override("en"):
            groups = {
                str(group["title"]): [str(item["title"]) for item in group["items"]]
                for group in response.context["sidebar_navigation"]
            }
        assert groups["Facilities"] == ["Departments", "Clinics", "Chairs", "Sessions", "Terms"]
        assert groups["Lists"][:2] == ["Case types", "Tooth codes"]
        assert groups["Settings"] == ["System settings"]

    def test_nothing_is_deleted(self, admin_client):
        clinic = Clinic.objects.create(number="5", name_ar="x", name_en="x", type="treatment")

        assert admin_client.get(f"/dashboard/setup/clinic/{clinic.pk}/delete/").status_code == 403


class TestClinics:
    def test_us01_create_clinic_5_with_12_chairs_through_the_service(self, admin_client):
        response = admin_client.post("/dashboard/setup/clinic/add/", clinic_data(chairs_to_add=12))

        assert response.status_code == 302, form_errors(response)
        clinic = Clinic.objects.get(number="5")
        assert list(clinic.chairs.values_list("number", flat=True)) == list(range(1, 13))
        assert AuditLog.objects.filter(model="setup.Clinic", action="create").count() == 1
        assert AuditLog.objects.get(model="setup.Clinic").user_id == admin_client.user.pk
        assert AuditLog.objects.filter(model="setup.Chair", action="create").count() == 12

    def test_us01_five_sessions_for_the_clinic(self, admin_client):
        admin_client.post("/dashboard/setup/clinic/add/", clinic_data())
        clinic = Clinic.objects.get(number="5")

        for order in range(1, 6):
            response = admin_client.post(
                "/dashboard/setup/session/add/",
                {
                    "clinic": clinic.pk,
                    "clinic_type": "",
                    "name_ar": f"الجلسة {order}",
                    "name_en": f"Session {order}",
                    "start_time": f"{7 + order:02d}:00",
                    "end_time": f"{7 + order:02d}:45",
                    "order": order,
                    "_save": "1",
                },
            )
            assert response.status_code == 302, form_errors(response)

        assert Session.objects.filter(clinic=clinic).count() == 5

    def test_the_change_page_lists_the_chairs(self, admin_client):
        admin_client.post("/dashboard/setup/clinic/add/", clinic_data(chairs_to_add=3))
        clinic = Clinic.objects.get(number="5")

        response = admin_client.get(f"/dashboard/setup/clinic/{clinic.pk}/change/")

        assert response.status_code == 200
        assert "Chair 3" in response.content.decode()

    def test_a_taken_number_shows_on_its_field_and_nothing_is_saved(self, admin_client):
        Clinic.objects.create(number="5", name_ar="x", name_en="x", type="lab", is_active=False)

        response = admin_client.post("/dashboard/setup/clinic/add/", clinic_data(chairs_to_add=4))

        assert "number" in form_errors(response)
        assert "already has this number" in str(form_errors(response)["number"])
        assert Clinic.all_objects.count() == 1
        assert not Chair.all_objects.exists()

    def test_a_page_shown_again_with_an_error_saves_nothing(self, admin_client):
        data = clinic_data(chairs_to_add=2)
        del data["chairs-TOTAL_FORMS"]  # the chairs table's part of the page is broken

        response = admin_client.post("/dashboard/setup/clinic/add/", data)

        assert response.status_code == 200
        assert not Clinic.all_objects.exists()
        assert not AuditLog.objects.filter(model="setup.Clinic").exists()

    def test_too_many_chairs_saves_neither_the_clinic_nor_the_chairs(self, admin_client):
        response = admin_client.post("/dashboard/setup/clinic/add/", clinic_data(chairs_to_add=101))

        assert "chairs_to_add" in form_errors(response)
        assert not Clinic.all_objects.exists()

    def test_change_keeps_the_values_the_form_does_not_show(self, admin_client):
        department = Department.objects.create(name_ar="اللبية", name_en="Endodontics")
        admin_client.post("/dashboard/setup/clinic/add/", clinic_data(department=department.pk))
        clinic = Clinic.objects.get(number="5")

        response = admin_client.post(
            f"/dashboard/setup/clinic/{clinic.pk}/change/",
            clinic_data(department=department.pk, floor="3"),
        )

        assert response.status_code == 302
        clinic.refresh_from_db()
        assert (clinic.floor, clinic.department_id) == ("3", department.pk)

    def test_deactivate_then_read_only(self, admin_client):
        clinic = Clinic.objects.create(number="5", name_ar="x", name_en="x", type="treatment")

        admin_client.post(
            "/dashboard/setup/clinic/",
            {"action": "deactivate_selected", "_selected_action": [clinic.pk]},
        )

        clinic.refresh_from_db()
        assert clinic.is_active is False
        response = admin_client.get(f"/dashboard/setup/clinic/{clinic.pk}/change/")
        assert response.context["has_change_permission"] is False
        assert AuditLog.objects.filter(action="deactivate", model="setup.Clinic").exists()


class TestChairs:
    @pytest.fixture
    def chair(self):
        clinic = Clinic.objects.create(number="5", name_ar="x", name_en="x", type="treatment")
        return Chair.objects.create(clinic=clinic, number=1)

    def test_out_of_service_with_a_reason_writes_history(self, admin_client, chair):
        url = f"/dashboard/setup/chair/{chair.pk}/status/"
        assert admin_client.get(url).status_code == 200

        response = admin_client.post(url, {"status": "out_of_service", "reason": "Broken light"})

        assert response.status_code == 302
        chair.refresh_from_db()
        assert chair.status == "out_of_service"
        change = ChairStatusChange.objects.get()
        assert (change.reason, change.by_id) == ("Broken light", admin_client.user.pk)
        page = admin_client.get(f"/dashboard/setup/chair/{chair.pk}/change/")
        assert "Broken light" in page.content.decode()

    def test_a_reason_is_required(self, admin_client, chair):
        response = admin_client.post(
            f"/dashboard/setup/chair/{chair.pk}/status/", {"status": "out_of_service"}
        )

        assert response.status_code == 200
        assert "reason" in response.context["form"].errors
        assert not ChairStatusChange.objects.exists()

    def test_us01_deactivating_a_chair_keeps_its_history(self, admin_client, chair):
        admin_client.post(
            f"/dashboard/setup/chair/{chair.pk}/status/",
            {"status": "out_of_service", "reason": "Leak"},
        )

        admin_client.post(
            "/dashboard/setup/chair/",
            {"action": "deactivate_selected", "_selected_action": [chair.pk]},
        )

        chair.refresh_from_db()
        assert chair.is_active is False
        assert ChairStatusChange.objects.filter(chair=chair).count() == 1
        assert admin_client.get(f"/dashboard/setup/chair/{chair.pk}/status/").status_code == 403


class TestLists:
    def test_a_tooth_code_letter_is_saved_in_upper_case(self, admin_client):
        response = admin_client.post(
            "/dashboard/setup/toothcode/add/",
            {
                "letter": "d",
                "meaning_ar": "نخر",
                "meaning_en": "Decayed",
                "color": "#D32F2F",
                "order": 1,
                "_save": "1",
            },
        )

        assert response.status_code == 302
        assert ToothCode.objects.get().letter == "D"

    def test_a_new_item_goes_to_the_end_of_the_list(self, admin_client):
        SoftTissueSite.objects.create(name_ar="الشفتان", name_en="Lips", order=4)

        response = admin_client.get("/dashboard/setup/softtissuesite/add/")

        assert response.context["adminform"].form.initial["order"] == 5

    def test_dragging_rows_saves_the_order_through_the_service(self, admin_client):
        lips = SoftTissueSite.objects.create(name_ar="الشفتان", name_en="Lips", order=1)
        tongue = SoftTissueSite.objects.create(name_ar="اللسان", name_en="Tongue", order=2)

        response = admin_client.post(
            "/dashboard/setup/softtissuesite/",
            {
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "2",
                "form-0-id": tongue.pk,
                "form-0-order": "1",
                "form-1-id": lips.pk,
                "form-1-order": "2",
                "_save": "Save",
            },
        )

        assert response.status_code == 302
        lips.refresh_from_db()
        tongue.refresh_from_db()
        assert (tongue.order, lips.order) == (1, 2)
        assert AuditLog.objects.filter(model="setup.SoftTissueSite", action="update").count() == 2


class TestSettings:
    @pytest.fixture
    def seeded(self):
        call_command("seed_defaults", stdout=StringIO())

    def test_one_page_with_every_setting(self, admin_client, seeded):
        response = admin_client.get("/dashboard/setup/systemsetting/")

        form = response.context["form"]
        assert form.initial["photo_max_mb"] == 2
        assert form.initial["round_morning_start"] == "08:30"

    def test_saves_through_the_service(self, admin_client, seeded):
        data = {**dict(SystemSetting.objects.values_list("key", "value")), "photo_max_mb": 5}
        data.pop("lookups_version")
        data["push_notifications_enabled"] = "on"

        response = admin_client.post("/dashboard/setup/systemsetting/", data)

        assert response.status_code == 302
        assert SystemSetting.objects.get(key="photo_max_mb").value == 5
        entry = AuditLog.objects.filter(model="setup.SystemSetting", action="update").get()
        assert entry.changes == {"photo_max_mb": {"old": 2, "new": 5}}

    def test_a_round_that_ends_before_it_starts_shows_on_its_field(self, admin_client, seeded):
        data = dict(SystemSetting.objects.values_list("key", "value"))
        data.pop("lookups_version")
        data["round_afternoon_end"] = "13:00"

        response = admin_client.post("/dashboard/setup/systemsetting/", data)

        assert response.status_code == 200
        assert "round_afternoon_end" in response.context["form"].errors
        assert SystemSetting.objects.get(key="round_afternoon_end").value == "15:00"


class TestTerms:
    def test_making_a_term_current_ends_the_previous_one(self, admin_client):
        values = {"start_date": "2026-09-14", "end_date": "2027-01-29", "_save": "1"}
        admin_client.post(
            "/dashboard/setup/term/add/", {"name": "Fall", "is_current": "on", **values}
        )
        admin_client.post(
            "/dashboard/setup/term/add/", {"name": "Spring", "is_current": "on", **values}
        )

        assert list(Term.objects.filter(is_current=True).values_list("name", flat=True)) == [
            "Spring"
        ]

    def test_the_current_term_cannot_be_deactivated(self, admin_client):
        term = Term.objects.create(
            name="Fall", start_date="2026-09-14", end_date="2027-01-29", is_current=True
        )

        response = admin_client.post(
            "/dashboard/setup/term/",
            {"action": "deactivate_selected", "_selected_action": [term.pk]},
            follow=True,
        )

        term.refresh_from_db()
        assert term.is_active is True
        assert "cannot be deactivated" in response.content.decode()


class TestArabic:
    def test_the_screens_are_in_arabic_by_default(self, dashboard):
        client = dashboard("super_admin")
        client.cookies.pop("django_language", None)

        page = client.get("/dashboard/setup/clinic/add/").content.decode()

        assert 'dir="rtl"' in page
        assert "عدد الكراسي المراد إضافتها" in page  # Chairs to add
        assert "الأقسام" in page  # Departments, in the sidebar

    def test_service_errors_are_in_arabic(self, dashboard):
        client = dashboard("super_admin")
        client.cookies.pop("django_language", None)
        Clinic.objects.create(number="5", name_ar="x", name_en="x", type="lab")

        response = client.post("/dashboard/setup/clinic/add/", clinic_data())

        assert "هذا الرقم مستخدم لعيادة أخرى" in str(form_errors(response)["number"])
