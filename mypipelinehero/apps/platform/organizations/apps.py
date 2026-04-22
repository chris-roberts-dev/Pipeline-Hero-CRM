"""AppConfig for the organizations package."""

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    name = "apps.platform.organizations"
    # Label is referenced by apps.common.tenancy.models.TenantModel's
    # string FK "organizations.Organization" — must match exactly.
    label = "organizations"
    verbose_name = "Organizations"
