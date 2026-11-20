"""Audit log (SYS-04): the diff, the ORM adapter and append-only rows."""

import datetime
from decimal import Decimal

import pytest
from django.test import RequestFactory, override_settings

from apps.core.application.ports import AuditLogger
from apps.core.domain.audit import AuditAction, diff
from apps.core.domain.errors import HardDeleteError
from apps.core.infrastructure.audit import OrmAuditLogger, model_label, snapshot
from apps.core.infrastructure.request_context import acting_as, bound_request
from apps.core.models import AuditLog
from tests.testapp.models import Note


class TestDiff:
    def test_lists_only_changed_fields(self):
        before = {"title": "a", "body": "same", "due": None}
        after = {"title": "b", "body": "same", "due": "2026-12-01"}

        assert diff(before, after) == {
            "title": {"old": "a", "new": "b"},
            "due": {"old": None, "new": "2026-12-01"},
        }

    def test_new_record_against_empty(self):
        assert diff({}, {"title": "a"}) == {"title": {"old": None, "new": "a"}}

    def test_removed_field(self):
        assert diff({"title": "a"}, {}) == {"title": {"old": "a", "new": None}}

    def test_no_change(self):
        assert diff({"title": "a"}, {"title": "a"}) == {}

    def test_actions_are_plain_strings(self):
        assert AuditAction.LOGIN_FAILED == "login_failed"


@pytest.mark.django_db
class TestSnapshot:
    def test_values_in_json_form_without_bookkeeping_fields(self, user):
        note = Note.objects.create(title="a", owner=user, due=datetime.date(2026, 12, 1))

        assert snapshot(note) == {
            "title": "a",
            "body": "",
            "owner": user.pk,
            "due": "2026-12-01",
            "is_active": True,
        }

    def test_exclude(self):
        note = Note.objects.create(title="a")

        assert "body" not in snapshot(note, exclude=["body"])

    def test_snapshot_diff_describes_a_change(self):
        note = Note.objects.create(title="a")
        before = snapshot(note)
        note.title = "b"
        note.deactivate()

        assert diff(before, snapshot(note)) == {
            "title": {"old": "a", "new": "b"},
            "is_active": {"old": True, "new": False},
        }

    def test_model_label(self):
        assert model_label(Note) == "testapp.Note"


@pytest.mark.django_db
class TestOrmAuditLogger:
    def test_fits_the_port(self):
        assert isinstance(OrmAuditLogger(), AuditLogger)

    def test_writes_a_row_with_the_request_user_and_ip(self, user):
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.7")
        request.user = user

        with bound_request(request):
            OrmAuditLogger().log(
                AuditAction.UPDATE,
                model="testapp.Note",
                object_id=12,
                changes={"title": {"old": "a", "new": "b"}, "cost": Decimal("1.50")},
            )

        row = AuditLog.objects.get()
        assert row.user == user
        assert row.action == "update"
        assert row.model == "testapp.Note"
        assert row.object_id == "12"
        assert row.changes == {"title": {"old": "a", "new": "b"}, "cost": "1.50"}
        assert row.ip == "10.0.0.7"
        assert row.at is not None

    def test_explicit_user_id_wins(self, make_user):
        actor, other = make_user("actor"), make_user("other")

        with acting_as(actor.pk):
            OrmAuditLogger().log(AuditAction.LOGIN_FAILED, user_id=other.pk)

        assert AuditLog.objects.get().user == other

    def test_login_failed_without_a_user(self):
        OrmAuditLogger().log(AuditAction.LOGIN_FAILED, changes={"username": "nobody"})

        row = AuditLog.objects.get()
        assert row.user is None
        assert row.ip is None
        assert row.model == ""
        assert row.object_id == ""

    @pytest.mark.urls("tests.testapp.urls")
    def test_through_an_api_request(self, api, user):
        api.post(
            "/api/v1/test/notes/create/", {"title": "a"}, format="json", REMOTE_ADDR="10.1.2.3"
        )

        row = AuditLog.objects.get()
        assert (row.user, row.action, row.model, row.ip) == (
            user,
            "create",
            "testapp.Note",
            "10.1.2.3",
        )

    @pytest.mark.urls("tests.testapp.urls")
    @override_settings(NUM_PROXIES=1)
    def test_ip_behind_the_proxy(self, api):
        api.post(
            "/api/v1/test/notes/create/",
            {"title": "a"},
            format="json",
            REMOTE_ADDR="172.18.0.2",
            HTTP_X_FORWARDED_FOR="203.0.113.9",
        )

        assert AuditLog.objects.get().ip == "203.0.113.9"


@pytest.mark.django_db
class TestAuditLogRows:
    def test_cannot_be_changed(self):
        OrmAuditLogger().log(AuditAction.LOGIN)
        row = AuditLog.objects.get()
        row.action = "logout"

        with pytest.raises(ValueError, match="never changed"):
            row.save()

    def test_cannot_be_deleted(self):
        OrmAuditLogger().log(AuditAction.LOGIN)

        with pytest.raises(HardDeleteError):
            AuditLog.objects.get().delete()

    def test_indexes_from_the_design(self):
        indexed = {tuple(index.fields) for index in AuditLog._meta.indexes}

        assert ("model", "object_id") in indexed
        assert ("at",) in indexed

    def test_newest_first(self):
        logger = OrmAuditLogger()
        logger.log("first")
        logger.log("second")

        assert list(AuditLog.objects.values_list("action", flat=True)) == ["second", "first"]
