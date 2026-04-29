"""AppConfig for the platform console (custom AdminSite + registrations).

Importing `apps.platform.console.admin` from `ready()` triggers admin
registrations across every app's `admin.py` via the central registry —
without us depending on Django's default `admin.autodiscover()` (which
would also try to populate the default admin.site, which we don't want).
"""

from django.apps import AppConfig


class ConsoleConfig(AppConfig):
    name = "apps.platform.console"
    label = "console"
    verbose_name = "Platform Console"

    def ready(self) -> None:
        # Importing the admin module triggers all the per-app registrations
        # against our custom site. Done in ready() so the imports happen
        # after every app's models are loaded.
        from apps.platform.console import admin  # noqa: F401
