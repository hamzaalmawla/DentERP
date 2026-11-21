"""Users and roles screens (DB-02): every change goes through an accounts service."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

USERS = "/dashboard/accounts/user/"


@pytest.fixture
def admin_client(dashboard):
    return dashboard("super_admin", username="admin")


def roles_of(user: User) -> set[str]:
    return set(user.user_roles.filter(is_active=True).values_list("role__code", flat=True))


def new_user_data(**values):
    return {
        "username": "Sara.Ali",
        "full_name_ar": "سارة علي",
        "full_name_en": "Sara Ali",
        "phone": "0999",
        "university_id": "",
        "roles": ["supervisor", "student"],
        "_save": "1",
        **values,
    }


class TestList:
    def test_lists_searches_and_filters(self, admin_client, make_user):
        make_user("sara", "student", full_name_ar="سارة")
        make_user("omar", "supervisor", full_name_ar="عمر")
        make_user("gone", "student").deactivate()
        make_user("locked", "student", locked_until=timezone.now() + timedelta(minutes=5))

        def usernames(query=""):
            response = admin_client.get(USERS + query)
            assert response.status_code == 200
            return {u.username for u in response.context["cl"].result_list}

        assert {"sara", "omar", "gone", "locked", "admin"} == usernames()
        assert usernames("?q=عمر") == {"omar"}
        assert usernames("?role=supervisor") == {"omar"}
        assert usernames("?is_active__exact=0") == {"gone"}
        assert usernames("?locked=yes") == {"locked"}


class TestCreate:
    def test_creates_through_the_service_and_shows_the_password_once(self, admin_client):
        response = admin_client.post(USERS + "add/", new_user_data())

        assert response.status_code == 200
        assert response.templates[0].name == "dashboard/temporary_password.html"
        assert "no-store" in response["Cache-Control"]
        password = response.context["temporary_password"]
        user = User.objects.get(username="sara.ali")
        assert user.check_password(password)
        assert user.must_change_password is True
        assert roles_of(user) == {"supervisor", "student"}
        entry = AuditLog.objects.get(action="create", object_id=str(user.pk))
        assert entry.user_id == admin_client.user.pk
        assert password not in str(entry.changes)

    @pytest.mark.parametrize(
        ("values", "field"),
        [
            ({"username": "ADMIN"}, "username"),
            ({"username": "has space"}, "username"),
            ({"roles": []}, "roles"),
            ({"full_name_ar": "   "}, "full_name_ar"),
        ],
    )
    def test_service_errors_show_on_their_field(self, admin_client, values, field):
        response = admin_client.post(USERS + "add/", new_user_data(**values))

        assert response.status_code == 200
        assert field in response.context["adminform"].form.errors
        assert not User.all_objects.filter(full_name_en="Sara Ali").exists()

    def test_the_error_summary_counts_the_errors_in_arabic(self, admin_client):
        del admin_client.cookies[settings.LANGUAGE_COOKIE_NAME]  # Arabic, the default

        response = admin_client.post(USERS + "add/", new_user_data(username="ADMIN"))

        html = response.content.decode()
        assert "الرجاء تصحيح الخطأ أدناه." in html
        assert "لا توجد أخطاء لتصحيحها" not in html

    def test_a_deactivated_users_username_is_taken(self, admin_client, make_user):
        make_user("sara.ali", "student").deactivate()

        response = admin_client.post(USERS + "add/", new_user_data())

        assert "already used" in str(response.context["adminform"].form.errors["username"])

    def test_university_id_taken(self, admin_client, make_user):
        make_user("other", "student", university_id="77")

        response = admin_client.post(USERS + "add/", new_user_data(university_id="77"))

        assert "university_id" in response.context["adminform"].form.errors


class TestChange:
    def test_changes_details_and_roles_through_the_services(self, admin_client, make_user):
        user = make_user("sara", "student", full_name_ar="سارة")
        data = {
            "full_name_ar": "سارة علي",
            "full_name_en": "Sara",
            "phone": "0911",
            "university_id": "2026",
            "roles": ["supervisor"],
            "_save": "1",
        }

        response = admin_client.post(f"{USERS}{user.pk}/change/", data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert (user.full_name_ar, user.phone, user.university_id) == ("سارة علي", "0911", "2026")
        assert roles_of(user) == {"supervisor"}
        assert AuditLog.objects.filter(action="update", object_id=str(user.pk)).count() == 2

    def test_the_form_shows_the_current_roles(self, admin_client, make_user):
        user = make_user("sara", "student", "supervisor")

        response = admin_client.get(f"{USERS}{user.pk}/change/")

        assert set(response.context["adminform"].form["roles"].initial) == {
            "student",
            "supervisor",
        }

    def test_one_failing_change_saves_neither(self, admin_client):
        admin = admin_client.user
        data = {
            "full_name_ar": "اسم جديد",
            "roles": ["supervisor"],  # the administrator may not drop their own admin role
            "_save": "1",
        }

        response = admin_client.post(f"{USERS}{admin.pk}/change/", data)

        assert "roles" in response.context["adminform"].form.errors
        admin.refresh_from_db()
        assert admin.full_name_ar != "اسم جديد"
        assert roles_of(admin) == {"super_admin"}

    def test_a_deactivated_user_is_read_only(self, admin_client, make_user):
        user = make_user("gone", "student")
        user.deactivate()

        response = admin_client.get(f"{USERS}{user.pk}/change/")

        assert response.status_code == 200
        assert response.context["has_change_permission"] is False


class TestActions:
    def test_reset_password_asks_first_then_shows_the_new_password(self, admin_client, make_user):
        user = make_user("sara", "student", locked_until=timezone.now() + timedelta(minutes=5))
        url = f"{USERS}{user.pk}/reset-password/"

        confirm = admin_client.get(url)
        assert confirm.templates[0].name == "dashboard/confirm_action.html"
        user.refresh_from_db()
        assert user.must_change_password is False

        response = admin_client.post(url)

        user.refresh_from_db()
        assert user.check_password(response.context["temporary_password"])
        assert user.must_change_password is True
        assert user.locked_until is None
        assert AuditLog.objects.filter(action="password_reset", object_id=str(user.pk)).exists()

    def test_unlock(self, admin_client, make_user):
        user = make_user("sara", "student", locked_until=timezone.now() + timedelta(minutes=5))

        response = admin_client.post(f"{USERS}{user.pk}/unlock/")

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.locked_until is None

    def test_unlock_an_account_that_is_not_locked_shows_the_error(self, admin_client, make_user):
        user = make_user("sara", "student")

        response = admin_client.post(f"{USERS}{user.pk}/unlock/", follow=True)

        assert "The account is not locked." in [str(m) for m in response.context["messages"]]

    def test_deactivate_asks_first_and_never_deletes(self, admin_client, make_user):
        user = make_user("sara", "student")
        url = f"{USERS}{user.pk}/deactivate/"

        assert admin_client.get(url).status_code == 200
        user.refresh_from_db()
        assert user.is_active

        response = admin_client.post(url)

        assert response.status_code == 302
        stored = User.all_objects.get(pk=user.pk)
        assert stored.is_active is False
        assert AuditLog.objects.filter(action="deactivate", object_id=str(user.pk)).exists()
        # A deactivated user has no actions left.
        assert admin_client.post(url).status_code == 403

    def test_the_administrator_cannot_deactivate_themselves(self, admin_client):
        admin = admin_client.user

        response = admin_client.post(f"{USERS}{admin.pk}/deactivate/", follow=True)

        assert "You cannot deactivate your own account." in [
            str(m) for m in response.context["messages"]
        ]
        admin.refresh_from_db()
        assert admin.is_active

    def test_an_unknown_user_is_not_found(self, admin_client):
        assert admin_client.get(f"{USERS}999999/reset-password/").status_code in (403, 404)
        assert admin_client.get(f"{USERS}abc/reset-password/").status_code in (403, 404)

    def test_unlock_selected(self, admin_client, make_user):
        soon = timezone.now() + timedelta(minutes=5)
        locked = [make_user(f"u{i}", "student", locked_until=soon) for i in range(2)]
        free = make_user("free", "student")

        response = admin_client.post(
            USERS,
            {
                "action": "unlock_selected",
                "_selected_action": [u.pk for u in [*locked, free]],
            },
            follow=True,
        )

        assert "Accounts unlocked: 2." in [str(m) for m in response.context["messages"]]
        assert not User.objects.filter(locked_until__isnull=False).exists()

    def test_the_actions_are_shown_on_the_user_page(self, admin_client, make_user):
        user = make_user("sara", "student")

        response = admin_client.get(f"{USERS}{user.pk}/change/")

        paths = {action["path"] for action in response.context["actions_detail"]}
        assert paths == {
            f"{USERS}{user.pk}/reset-password/",
            f"{USERS}{user.pk}/unlock/",
            f"{USERS}{user.pk}/deactivate/",
        }


class TestRoles:
    def test_lists_the_roles_read_only_with_their_users(self, admin_client, make_user):
        make_user("a", "student")
        make_user("b", "student")
        make_user("c", "student").deactivate()

        response = admin_client.get("/dashboard/accounts/role/")

        counts = {role.code: role.active_users for role in response.context["cl"].result_list}
        assert counts["student"] == 2
        assert counts["super_admin"] == 1
        assert response.context["has_add_permission"] is False
        role_id = response.context["cl"].result_list[0].pk
        page = admin_client.get(f"/dashboard/accounts/role/{role_id}/change/")
        assert page.context["has_change_permission"] is False
        assert (
            admin_client.post(f"/dashboard/accounts/role/{role_id}/change/", {}).status_code == 403
        )
