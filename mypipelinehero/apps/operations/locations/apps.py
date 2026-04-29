"""AppConfig for the operations.locations package."""

from django.apps import AppConfig


class LocationsConfig(AppConfig):
    name = "apps.operations.locations"
    label = "locations"
    verbose_name = "Operating Scope (Region/Market/Location)"
