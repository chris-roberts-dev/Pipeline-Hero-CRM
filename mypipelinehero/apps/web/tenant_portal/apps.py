"""AppConfig for the tenant portal."""
from django.apps import AppConfig


class TenantPortalConfig(AppConfig):
    name = "apps.web.tenant_portal"
    label = "tenant_portal"
    verbose_name = "Tenant Portal"
