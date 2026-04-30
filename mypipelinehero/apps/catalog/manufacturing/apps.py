"""
Catalog manufacturing app.

Owns:
  - BOM: Bill of Materials for a manufactured Product. Tracks version,
    effective_from date, and a DRAFT → ACTIVE → SUPERSEDED workflow.
    At most one BOM per finished_product is ACTIVE at any time
    (enforced via partial unique index).
  - BOMLine: a single material requirement within a BOM. Stores both
    the human-meaningful quantity (in the line's chosen UoM) and the
    cost-basis quantity (in the RawMaterial's catalog UoM) — see the
    BOMLine docstring for the dual-quantity rationale.

App label is `catalog_manufacturing`.

Pricing role (per spec §13.1): manufactured Product cost rolls up as
  sum(BOMLine.cost_basis_quantity × BOMLine.cost_reference) + labor.
Labor is tracked separately (§15.3 — out of M3 scope).
"""

from django.apps import AppConfig


class CatalogManufacturingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog.manufacturing"
    label = "catalog_manufacturing"
    verbose_name = "Catalog: Manufacturing"
