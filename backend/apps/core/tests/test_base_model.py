"""BaseModel: soft delete (SYS-10) and created_by / updated_by."""

import pytest
from django.test import RequestFactory

from apps.core.domain.errors import HardDeleteError
from apps.core.infrastructure.request_context import acting_as, bound_request
from tests.testapp.models import Note

pytestmark = pytest.mark.django_db


class TestSoftDelete:
    def test_delete_raises(self):
        note = Note.objects.create(title="a")

        with pytest.raises(HardDeleteError) as error:
            note.delete()

        assert error.value.code == "delete_not_allowed"
        assert Note.all_objects.filter(pk=note.pk).exists()

    def test_queryset_delete_raises_on_both_managers(self):
        Note.objects.create(title="a")

        with pytest.raises(HardDeleteError):
            Note.objects.all().delete()
        with pytest.raises(HardDeleteError):
            Note.all_objects.filter(title="a").delete()
        assert Note.all_objects.count() == 1

    def test_deactivate_hides_the_row_and_all_objects_still_sees_it(self):
        note = Note.objects.create(title="a")
        other = Note.objects.create(title="b")

        note.deactivate()

        assert list(Note.objects.all()) == [other]
        assert set(Note.all_objects.all()) == {note, other}
        assert Note.all_objects.get(pk=note.pk).is_active is False

    def test_activate_shows_the_row_again(self):
        note = Note.objects.create(title="a")
        note.deactivate()

        note.activate()

        assert Note.objects.filter(pk=note.pk).exists()

    def test_queryset_deactivate(self, user):
        Note.objects.create(title="a")
        Note.objects.create(title="b")

        with acting_as(user.pk):
            count = Note.objects.filter(title="a").deactivate()

        assert count == 1
        assert list(Note.objects.values_list("title", flat=True)) == ["b"]
        assert Note.all_objects.get(title="a").updated_by == user

    def test_new_rows_are_active(self):
        assert Note.objects.create(title="a").is_active is True


class TestUserFields:
    def test_filled_from_the_request_user(self, user):
        request = RequestFactory().get("/")
        request.user = user

        with bound_request(request):
            note = Note.objects.create(title="a")

        note.refresh_from_db()
        assert note.created_by == user
        assert note.updated_by == user

    def test_filled_from_acting_as(self, user):
        with acting_as(user.pk):
            note = Note.objects.create(title="a")

        assert note.created_by_id == user.pk
        assert note.updated_by_id == user.pk

    def test_acting_as_wins_over_the_request(self, make_user):
        request_user, actor = make_user("req"), make_user("actor")
        request = RequestFactory().get("/")
        request.user = request_user

        with bound_request(request), acting_as(actor.pk):
            note = Note.objects.create(title="a")

        assert note.created_by_id == actor.pk

    def test_update_keeps_created_by_and_sets_updated_by(self, make_user):
        author, editor = make_user("author"), make_user("editor")
        with acting_as(author.pk):
            note = Note.objects.create(title="a")

        with acting_as(editor.pk):
            note.title = "b"
            note.save()

        note.refresh_from_db()
        assert note.created_by_id == author.pk
        assert note.updated_by_id == editor.pk

    def test_save_with_update_fields_still_records_the_editor(self, make_user):
        author, editor = make_user("author"), make_user("editor")
        with acting_as(author.pk):
            note = Note.objects.create(title="a")
        updated_at = note.updated_at

        with acting_as(editor.pk):
            note.title = "b"
            note.save(update_fields=["title"])

        note.refresh_from_db()
        assert note.updated_by_id == editor.pk
        assert note.updated_at > updated_at

    def test_deactivate_records_who_did_it(self, make_user):
        author, editor = make_user("author"), make_user("editor")
        with acting_as(author.pk):
            note = Note.objects.create(title="a")

        with acting_as(editor.pk):
            note.deactivate()

        assert Note.all_objects.get(pk=note.pk).updated_by_id == editor.pk

    def test_empty_without_a_user(self):
        note = Note.objects.create(title="a")

        assert note.created_by is None
        assert note.updated_by is None

    def test_anonymous_request_counts_as_no_user(self):
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        with bound_request(request):
            note = Note.objects.create(title="a")

        assert note.created_by is None

    def test_change_by_the_system_clears_updated_by(self, user):
        with acting_as(user.pk):
            note = Note.objects.create(title="a")

        with acting_as(None):
            note.title = "b"
            note.save()

        assert note.created_by_id == user.pk
        assert note.updated_by_id is None

    @pytest.mark.urls("tests.testapp.urls")
    def test_filled_through_the_middleware_on_an_api_request(self, api, user):
        """DRF authenticates inside the view (as with JWT); the user is still seen at save time."""
        response = api.post("/api/v1/test/notes/create/", {"title": "a"}, format="json")

        assert response.status_code == 201
        note = Note.objects.get(pk=response.json()["id"])
        assert note.created_by == user
        assert note.updated_by == user
