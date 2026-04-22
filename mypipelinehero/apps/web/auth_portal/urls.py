"""URL patterns for the auth portal (root-domain org picker + handoff issuer)."""

from django.urls import path

from . import views

app_name = "auth_portal"

urlpatterns = [
    path("auth/pick/", views.pick_organization, name="pick_organization"),
    path("auth/handoff/", views.issue_handoff, name="issue_handoff"),
]
