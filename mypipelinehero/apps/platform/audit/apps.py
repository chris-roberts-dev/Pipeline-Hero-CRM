"""AppConfig for the audit package."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.platform.audit"
    label = "audit"
    verbose_name = "Audit"
