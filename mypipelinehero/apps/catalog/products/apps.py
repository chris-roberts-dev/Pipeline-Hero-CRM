"""
Catalog products app.

Owns:
  - Product: physical item; either RESALE (purchased externally) or
    MANUFACTURED (built in-house)

App label is `catalog_products` — explicit naming over the last-segment
convention. Avoids any future collision with another app named `products`,
and makes FK strings (`"catalog_products.Product"`) self-documenting about
which catalog subdomain owns the model.

In later M3 steps this app will gain inline relationships to suppliers and
materials, but Product itself stays here.
"""

from django.apps import AppConfig


class CatalogProductsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog.products"
    label = "catalog_products"
    verbose_name = "Catalog: Products"
