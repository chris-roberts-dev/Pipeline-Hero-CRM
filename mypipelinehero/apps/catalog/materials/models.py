"""
RawMaterial model.

A RawMaterial is an input consumed by a manufactured product's BOM. Unlike
a Product (which is sold to customers), raw materials are *purchased* and
*consumed*. The pricing engine reads `current_cost` when computing a BOM
roll-up cost; the BOMLine model (later M3 step) records the quantity of
each material consumed per finished unit.

Inherits `TenantModel` from apps.common.tenancy.models, which provides:
  - organization FK (PROTECT, related_name="+")
  - created_at / updated_at
  - `objects = TenantManager()` with `.for_org(org)` for queryset scoping

Index/constraint names use the `mat_` prefix and stay under Django's
30-char limit on index identifiers.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.decimal_precision import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.common.tenancy.models import TenantModel


class RawMaterial(TenantModel):
    """A raw material consumed by manufactured products.

    Pricing role (per spec §13.1):
      - Manufactured product cost = sum(BOMLine.quantity × RawMaterial.current_cost) + labor
      - `current_cost` is the *latest* known per-unit cost; it changes when
        a supplier price changes. Historical pricing snapshots (M3 step 4)
        capture the value at quote time so price changes don't retroactively
        affect issued quotes.

    `current_cost` is allowed to be zero (a placeholder for a material
    whose cost hasn't been entered yet) but never negative. Negative-cost
    materials are nonsensical at the catalog level — that's a pricing-rule
    concern (§13.1: "Negative markup blocked at PricingRule validation").
    """

    class UnitOfMeasure(models.TextChoices):
        # Discrete count
        EACH = "EACH", "Each"
        # Mass
        KG = "KG", "Kilogram"
        G = "G", "Gram"
        LB = "LB", "Pound"
        OZ = "OZ", "Ounce"
        # Volume (liquid)
        L = "L", "Liter"
        ML = "ML", "Milliliter"
        GAL = "GAL", "Gallon"
        FL_OZ = "FL_OZ", "Fluid Ounce"
        # Length
        M = "M", "Meter"
        FT = "FT", "Foot"
        # Area
        M2 = "M2", "Square Meter"
        FT2 = "FT2", "Square Foot"
        # Bulk volume
        M3 = "M3", "Cubic Meter"
        FT3 = "FT3", "Cubic Foot"
        # Escape hatch — flagged as "Other" in UI; intentionally last so it
        # doesn't appear at the top of dropdowns. Use sparingly; if a unit
        # is needed often enough to use OTHER repeatedly, it should become
        # its own enum entry.
        OTHER = "OTHER", "Other"

    sku = models.CharField(
        max_length=64,
        help_text="Stock keeping unit — unique within an organization.",
    )
    name = models.CharField(max_length=200)
    unit_of_measure = models.CharField(
        max_length=10,
        choices=UnitOfMeasure.choices,
        help_text=(
            "Unit pricing math is in. Cost values for this material are "
            "interpreted as cost-per-unit-of-measure. Mismatched units are "
            "a real data-quality risk; choose deliberately."
        ),
    )
    current_cost = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=(
            "Latest known per-unit cost. Updated when a supplier price "
            "change is recorded. Historical snapshots preserve the value "
            "at quote time."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Soft-disable flag. Inactive materials are hidden from the "
            "BOM picker but retained for historical references."
        ),
    )

    class Meta:
        verbose_name = "raw material"
        verbose_name_plural = "raw materials"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "sku"),
                name="mat_rawmaterial_uniq_org_sku",
            ),
        ]
        indexes = [
            # Browse path mirrors Product/Service (org+is_active+name).
            models.Index(
                fields=("organization", "is_active", "name"),
                name="mat_rawmaterial_org_act_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"
