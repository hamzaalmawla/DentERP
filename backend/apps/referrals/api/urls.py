"""Referrals routes under /api/v1/ (design section 7)."""

from django.urls import path

from . import views

app_name = "referrals"

urlpatterns = [
    path("referrals/", views.ReferralListView.as_view(), name="referral-list"),
    path("referrals/<int:pk>/accept/", views.ReferralAcceptView.as_view(), name="referral-accept"),
    path("referrals/<int:pk>/reject/", views.ReferralRejectView.as_view(), name="referral-reject"),
    path("referrals/<int:pk>/assign/", views.ReferralAssignView.as_view(), name="referral-assign"),
    path(
        "referrals/<int:pk>/eligible-students/",
        views.ReferralEligibleStudentsView.as_view(),
        name="referral-eligible-students",
    ),
]
