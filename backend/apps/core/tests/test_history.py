"""Full history with django-simple-history, set up through track_history()."""

import pytest
from django.test import RequestFactory

from apps.core.infrastructure.request_context import acting_as, bound_request
from tests.testapp.models import Note

pytestmark = pytest.mark.django_db


def test_history_row_on_create_and_change():
    note = Note.objects.create(title="a")
    note.title = "b"
    note.save()

    versions = list(note.history.order_by("history_id"))
    assert [(v.history_type, v.title) for v in versions] == [("+", "a"), ("~", "b")]


def test_history_diff_between_versions():
    note = Note.objects.create(title="a")
    note.title = "b"
    note.save()

    newest, previous = note.history.all()[:2]
    changes = newest.diff_against(previous).changes

    assert [(c.field, c.old, c.new) for c in changes] == [("title", "a", "b")]


def test_history_records_the_acting_user(user):
    with acting_as(user.pk):
        note = Note.objects.create(title="a")

    assert note.history.get().history_user == user


def test_history_records_the_request_user(user):
    request = RequestFactory().get("/")
    request.user = user

    with bound_request(request):
        note = Note.objects.create(title="a")

    assert note.history.get().history_user == user


def test_history_without_a_user():
    note = Note.objects.create(title="a")

    assert note.history.get().history_user is None


def test_deactivate_is_a_new_version():
    note = Note.objects.create(title="a")

    note.deactivate()

    assert note.history.first().is_active is False
    assert note.history.count() == 2
