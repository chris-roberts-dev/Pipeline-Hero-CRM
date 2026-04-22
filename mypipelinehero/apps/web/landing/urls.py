"""URL patterns for the landing (root-domain) views."""

from django.urls import path

from . import views

app_name = "landing"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("no-access/", views.no_access_view, name="no_access"),
    path(
        "platform/",
        views.platform_console_placeholder,
        name="platform_console",
    ),
]
