"""
Catalog materials app.

Owns:
  - RawMaterial: input material consumed by a manufactured product's BOM.
    Has a current_cost (the latest known per-unit cost) and a unit of measure
    that pricing/BOM math depends on.

App label is `catalog_materials` — explicit naming, matching step 1's
convention for `catalog_services` / `catalog_products`.

Later M3 steps will add BOM and BOMLine models in `apps.catalog.manufacturing`,
which will FK into RawMaterial here.
"""

from django.apps import AppConfig


class CatalogMaterialsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog.materials"
    label = "catalog_materials"
    verbose_name = "Catalog: Raw Materials"
