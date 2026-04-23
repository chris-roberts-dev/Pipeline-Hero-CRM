"""AppConfig for the RBAC package."""

from django.apps import AppConfig


class RbacConfig(AppConfig):
    name = "apps.platform.rbac"
    label = "rbac"
    verbose_name = "RBAC"
