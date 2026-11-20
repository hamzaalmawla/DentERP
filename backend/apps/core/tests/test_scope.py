"""Scope (design section 8): a row outside the user's scope is a 404, like a missing row."""

import pytest

from apps.core.application.dtos import Actor
from apps.core.application.scope import ScopedQueryService, found_or_404
from apps.core.domain.errors import NotFoundError
from tests.testapp.models import Note
from tests.testapp.queries import NOTE_SCOPE


class FakeRepository:
    def __init__(self, rows: dict[int, tuple[int, str]]) -> None:
        self.rows = rows  # pk -> (owner id, title)

    def get_in_scope(self, actor: Actor, pk: int) -> str | None:
        row = self.rows.get(pk)
        return row[1] if row and row[0] == actor.user_id else None


class TitleQueries(ScopedQueryService[str]):
    def __init__(self, repository: FakeRepository) -> None:
        self._repository = repository

    def _get_in_scope(self, actor: Actor, pk: int) -> str | None:
        return self._repository.get_in_scope(actor, pk)


class TestScopedQueryService:
    """No database: the query service over an in-memory fake of its repository port."""

    queries = TitleQueries(FakeRepository({1: (10, "mine"), 2: (20, "theirs")}))

    def test_row_in_scope(self):
        assert self.queries.get(Actor(10, "student"), 1) == "mine"

    def test_row_outside_scope_is_not_found(self):
        with pytest.raises(NotFoundError) as error:
            self.queries.get(Actor(10, "student"), 2)

        assert error.value.code == "not_found"

    def test_missing_row_is_the_same_error(self):
        with pytest.raises(NotFoundError):
            self.queries.get(Actor(10, "student"), 999)

    def test_found_or_404(self):
        assert found_or_404(0) == 0  # falsy values are still found
        with pytest.raises(NotFoundError):
            found_or_404(None)


@pytest.mark.django_db
class TestRoleScope:
    @pytest.fixture
    def rows(self, make_user):
        alice, bob = make_user("alice"), make_user("bob")
        return (
            alice,
            bob,
            Note.objects.create(title="a", owner=alice),
            Note.objects.create(title="b", owner=bob),
        )

    def test_rule_limits_the_rows(self, rows):
        alice, _, note_a, _ = rows

        assert list(NOTE_SCOPE.filter(Note.objects.all(), Actor(alice.pk, "student"))) == [note_a]

    def test_everything(self, rows):
        alice, *_ = rows

        assert NOTE_SCOPE.filter(Note.objects.all(), Actor(alice.pk, "management")).count() == 2

    def test_role_without_a_rule_sees_nothing(self, rows):
        alice, *_ = rows

        assert not NOTE_SCOPE.filter(Note.objects.all(), Actor(alice.pk, "technician")).exists()

    def test_get_outside_scope_is_none(self, rows):
        alice, _, note_a, note_b = rows
        actor = Actor(alice.pk, "student")

        assert NOTE_SCOPE.get(Note.objects, actor, note_a.pk) == note_a
        assert NOTE_SCOPE.get(Note.objects, actor, note_b.pk) is None

    def test_inactive_rows_are_out_of_scope_through_objects(self, rows):
        alice, _, note_a, _ = rows
        note_a.deactivate()

        assert NOTE_SCOPE.get(Note.objects, Actor(alice.pk, "student"), note_a.pk) is None


@pytest.mark.django_db
@pytest.mark.urls("tests.testapp.urls")
class TestScopeOverTheApi:
    def test_own_row(self, api, user):
        note = Note.objects.create(title="mine", owner=user)

        response = api.get(f"/api/v1/test/notes/{note.pk}/", HTTP_X_ACTIVE_ROLE="student")

        assert response.status_code == 200
        assert response.json() == {"id": note.pk, "title": "mine"}

    def test_row_outside_scope_returns_404_in_the_error_format(self, api, make_user):
        note = Note.objects.create(title="theirs", owner=make_user("bob"))

        response = api.get(
            f"/api/v1/test/notes/{note.pk}/",
            HTTP_X_ACTIVE_ROLE="student",
            HTTP_ACCEPT_LANGUAGE="ar",
        )

        assert response.status_code == 404
        assert response.json() == {
            "code": "not_found",
            "message": "السجل غير موجود.",
            "details": {},
        }

    def test_outside_scope_and_missing_look_the_same(self, api, make_user):
        note = Note.objects.create(title="theirs", owner=make_user("bob"))

        outside = api.get(f"/api/v1/test/notes/{note.pk}/", HTTP_X_ACTIVE_ROLE="student")
        missing = api.get("/api/v1/test/notes/999999/", HTTP_X_ACTIVE_ROLE="student")

        assert (outside.status_code, outside.json()) == (missing.status_code, missing.json())
