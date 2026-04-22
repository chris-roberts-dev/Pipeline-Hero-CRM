"""AppConfig for the tenancy base package."""

from django.apps import AppConfig


class TenancyConfig(AppConfig):
    name = "apps.common.tenancy"
    label = "tenancy"
    verbose_name = "Tenancy base"
