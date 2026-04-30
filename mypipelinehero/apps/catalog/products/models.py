"""
Product model.

Single model in this file:
  - Product: physical item; either RESALE (purchased externally) or
    MANUFACTURED (built in-house)

Inherits `TenantModel` from apps.common.tenancy.models, which provides:
  - organization FK (PROTECT, related_name="+")
  - created_at / updated_at
  - `objects = TenantManager()` with `.for_org(org)` for queryset scoping

No catalog_price here — unlike Service, product pricing inputs come from
upstream tables (supplier cost or BOM cost), not a flat field on the
product itself. That's exactly the v1 strategy-pattern split from §13.1.

Index/constraint names use the `prod_` prefix and stay under Django's
30-char limit on index identifiers.
"""

from __future__ import annotations

from django.db import models

from apps.common.tenancy.models import TenantModel


class Product(TenantModel):
    """A physical product the organization sells.

    Two product types per spec §12.3 / §12.4:
      - RESALE: purchased from a supplier and resold. Pricing strategy reads
        the supplier unit cost; supplier linkage arrives via SupplierProduct
        in a later M3 step (apps.catalog.suppliers).
      - MANUFACTURED: built in-house from a BOM. Pricing strategy reads the
        BOM material cost + estimated labor; BOM model arrives in a later
        M3 step (apps.catalog.manufacturing).
    """

    class ProductType(models.TextChoices):
        RESALE = "RESALE", "Resale"
        MANUFACTURED = "MANUFACTURED", "Manufactured"

    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        help_text=(
            "RESALE products are purchased externally and resold. "
            "MANUFACTURED products are built in-house from a BOM."
        ),
    )
    sku = models.CharField(
        max_length=64,
        help_text="Stock keeping unit — unique within an organization.",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Soft-disable flag. Inactive products are hidden from the "
            "quote-line picker but retained for historical references."
        ),
    )

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "sku"),
                name="prod_product_uniq_org_sku",
            ),
        ]
        indexes = [
            # Browse path.
            models.Index(
                fields=("organization", "is_active", "name"),
                name="prod_product_org_active_idx",
            ),
            # Type-filtered browse: "show me active resale products" — the
            # quote-line picker filters by product_type to drive different
            # downstream forms (supplier picker for RESALE vs BOM viewer
            # for MANUFACTURED).
            models.Index(
                fields=("organization", "product_type", "is_active"),
                name="prod_product_org_type_act_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"
