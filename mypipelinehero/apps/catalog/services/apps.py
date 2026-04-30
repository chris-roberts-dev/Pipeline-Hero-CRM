"""
Catalog services app.

Owns:
  - ServiceCategory: org-scoped grouping for services
  - Service: work-performed-for-client; flat catalog price (v1 pricing input)

App label is `catalog_services` — explicit naming over the last-segment
convention. Avoids any future collision with another app named `services`,
and makes FK strings (`"catalog_services.ServiceCategory"`) self-documenting
about which catalog subdomain owns the model.
"""

from django.apps import AppConfig


class CatalogServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog.services"
    label = "catalog_services"
    verbose_name = "Catalog: Services"
