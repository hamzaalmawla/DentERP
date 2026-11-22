"""Media routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "media"

urlpatterns = [
    path("media/", views.MediaUploadView.as_view(), name="media-upload"),
    path("media/<int:pk>/", views.MediaDetailView.as_view(), name="media-detail"),
]
