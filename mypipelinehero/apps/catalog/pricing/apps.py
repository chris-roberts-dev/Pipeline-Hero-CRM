"""
Catalog pricing app.

Owns:
  - PricingRule: how a price is computed for a given line type and item.
    `target_line_type` plus optional `target_service`/`target_product`
    determine which lines a rule applies to; `parameters` (JSON) carries
    the rule_type-specific math (e.g. markup percent).
  - PricingSnapshot: immutable record of a computed price at quote time.
    Snapshots are written once and never updated. Re-pricing creates a
    new snapshot and flips the previous one to is_active=False (per spec
    §13.3 "superseded snapshots from re-pricing are retained").

App label is `catalog_pricing`.

This step (4a) lands models + migrations + tests only. The pricing
strategy engine itself (PricingContext, PricingStrategy implementations,
the dispatch registry) lives in step 4b — invoked from the service layer,
never from views/templates/save() (per §13.1 line 1120).
"""

from django.apps import AppConfig


class CatalogPricingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog.pricing"
    label = "catalog_pricing"
    verbose_name = "Catalog: Pricing"
