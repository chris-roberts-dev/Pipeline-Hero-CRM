"""AppConfig for the landing (root-domain) app."""
from django.apps import AppConfig


class LandingConfig(AppConfig):
    name = "apps.web.landing"
    label = "landing"
    verbose_name = "Landing"
