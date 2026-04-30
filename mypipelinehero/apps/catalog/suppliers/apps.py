"""
Catalog suppliers app.

Owns:
  - Supplier: external party we purchase from.
  - SupplierProduct: join table linking a Supplier to either a Product
    (`catalog_products.Product`) or a RawMaterial
    (`catalog_materials.RawMaterial`). Holds the per-supplier sku and
    default_cost, used as the base cost for resale pricing (§13.1).

App label is `catalog_suppliers` — explicit naming, matching step 1's
convention.

Migration dependency note: `catalog_suppliers.0001_initial` depends on
`organizations.0001_initial`, `catalog_products.0001_initial`, AND
`catalog_materials.0001_initial`. Django's autodetector emits these
correctly because the FKs reference those apps.
"""

from django.apps import AppConfig


class CatalogSuppliersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog.suppliers"
    label = "catalog_suppliers"
    verbose_name = "Catalog: Suppliers"
