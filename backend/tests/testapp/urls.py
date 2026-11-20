"""The project's URLs plus test-only endpoints (use with ``pytest.mark.urls``)."""

from django.urls import path

from config.urls import urlpatterns as project_urlpatterns

from . import views

urlpatterns = [
    *project_urlpatterns,
    path("api/v1/test/domain-error/", views.DomainErrorView.as_view()),
    path("api/v1/test/domain-error-params/", views.DomainErrorWithParamsView.as_view()),
    path("api/v1/test/conflict/", views.ConflictView.as_view()),
    path("api/v1/test/validation/", views.ValidationView.as_view()),
    path("api/v1/test/django-validation/", views.DjangoValidationView.as_view()),
    path("api/v1/test/not-found/", views.NotFoundView.as_view()),
    path("api/v1/test/permission-denied/", views.PermissionDeniedView.as_view()),
    path("api/v1/test/notes/", views.NoteListView.as_view()),
    path("api/v1/test/notes/create/", views.NoteCreateView.as_view()),
    path("api/v1/test/notes/<int:pk>/", views.ScopedNoteView.as_view()),
]
