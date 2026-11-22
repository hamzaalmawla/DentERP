"""Workcards routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "workcards"

urlpatterns = [
    path("workcards/", views.WorkCardListView.as_view(), name="workcard-list"),
    path("workcards/<int:pk>/", views.WorkCardDetailView.as_view(), name="workcard-detail"),
    path("cases/<int:pk>/", views.CaseDetailView.as_view(), name="case-detail"),
    path("cases/<int:pk>/complete/", views.CaseCompleteView.as_view(), name="case-complete"),
    path("steps/<int:pk>/submit/", views.StepSubmitView.as_view(), name="step-submit"),
    path("steps/<int:pk>/approve/", views.StepApproveView.as_view(), name="step-approve"),
    path("steps/<int:pk>/return/", views.StepReturnView.as_view(), name="step-return"),
    path("approvals/", views.ApprovalsView.as_view(), name="approvals"),
]
