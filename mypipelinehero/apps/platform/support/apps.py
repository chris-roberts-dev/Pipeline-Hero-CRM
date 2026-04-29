"""AppConfig for the platform support tooling package."""

from django.apps import AppConfig


class SupportConfig(AppConfig):
    name = "apps.platform.support"
    label = "support"
    verbose_name = "Platform Support Tooling"
