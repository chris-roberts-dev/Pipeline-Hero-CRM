"""AppConfig for the auth portal (org picker + handoff issuer)."""
from django.apps import AppConfig


class AuthPortalConfig(AppConfig):
    name = "apps.web.auth_portal"
    label = "auth_portal"
    verbose_name = "Auth Portal"
