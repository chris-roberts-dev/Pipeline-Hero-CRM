"""AppConfig for the tenancy base package."""

from django.apps import AppConfig


class TenancyConfig(AppConfig):
    name = "apps.common.tenancy"
    # Short label — the default would be "tenancy" which is fine. Making it
    # explicit so refactoring this path later doesn't silently change the
    # app_label and orphan migrations.
    label = "tenancy"
    verbose_name = "Tenancy base"
