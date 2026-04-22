"""URL patterns for the tenant portal (tenant subdomain)."""

from django.urls import path

from . import views

app_name = "tenant_portal"

urlpatterns = [
    path("auth/handoff", views.handoff_completion, name="handoff"),
    path("auth/logout/", views.tenant_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
]
