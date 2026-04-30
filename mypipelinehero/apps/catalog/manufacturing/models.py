"""
BOM and BOMLine models.

Two models in this file:
  - BOM: parent record with version, effective_from, status workflow.
  - BOMLine: per-material line item with dual-quantity (display + cost basis).

Key design decisions:

1. **Free-text version label.** `BOM.version` is a CharField, not an
   auto-incrementing integer. Manufacturers often have meaningful version
   codes from external systems ("2025-Q1-rev2"); forcing auto-increment
   fights that.

2. **At most one ACTIVE BOM per finished_product** is enforced by a
   partial unique index `WHERE status = 'ACTIVE'`. Same Postgres pattern
   as M3 step 2's SupplierProduct partial uniques.

3. **No DB-level effective_from CHECK.** Date/status workflow rules
   (DRAFT can be future, ACTIVE/SUPERSEDED must be past-or-today) are
   workflow concerns enforced in `clean()`, not data-integrity invariants.

4. **Dual-quantity BOMLine.** `quantity` + `unit_of_measure` are the
   human-readable specification ("use 3 KG"); `cost_basis_quantity` is
   the same physical amount expressed in the RawMaterial's catalog UoM
   (e.g. "= 0.25 M2 of steel"). Pricing math uses cost_basis_quantity ×
   cost_reference and never needs to know about unit conversion. The
   user does the conversion at entry time.

5. **`cost_reference` lifecycle.** Tracks `RawMaterial.current_cost`
   live while the BOM is DRAFT, frozen on transition to ACTIVE.
   Step-3 only stores the field; the lifecycle behavior lives in the
   service layer (M3 step 4).

6. **`unit_of_measure` enum sharing.** BOMLine reuses
   `RawMaterial.UnitOfMeasure.choices` rather than re-declaring. Cross-app
   import is acceptable here because we already import RawMaterial for
   the FK target.

7. **CASCADE on BOMLine.bom; PROTECT on BOMLine.raw_material.** Lines
   are intrinsic to their BOM; raw materials are catalog records that
   should never disappear silently while referenced anywhere.

Index/constraint name prefix: `bom_`, all ≤30 chars.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.materials.models import RawMaterial
from apps.common.decimal_precision import (
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
    QUANTITY_DECIMAL_PLACES,
    QUANTITY_MAX_DIGITS,
)
from apps.common.tenancy.models import TenantModel


class BOM(TenantModel):
    """Bill of Materials for a manufactured Product.

    Per spec §15.2: "Old BOM versions remain accessible for audit and cost
    comparison." That's enforced here by SUPERSEDED status (the row is
    retained, not deleted) and by PROTECT on referenced raw materials
    in BOMLine — a SUPERSEDED BOM still pins the RawMaterials it used.

    Lifecycle (managed by service-layer methods in M3 step 4):
      - DRAFT: editable; cost_reference values track RawMaterial.current_cost
      - ACTIVE: immutable; only one per finished_product at a time
      - SUPERSEDED: immutable; previous ACTIVE BOMs land here when a new
        one activates
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        SUPERSEDED = "SUPERSEDED", "Superseded"

    finished_product = models.ForeignKey(
        "catalog_products.Product",
        on_delete=models.PROTECT,
        related_name="boms",
        help_text=(
            "The Product this BOM produces. Should be a MANUFACTURED-type "
            "product; this is enforced at the service layer, not the DB."
        ),
    )
    version = models.CharField(
        max_length=64,
        help_text=(
            "Free-text version label (e.g. 'v2.1', '2025-Q1-rev2'). "
            "Unique per (organization, finished_product) so two BOMs for "
            "the same product can't share a version string."
        ),
    )
    effective_from = models.DateField(
        help_text=(
            "Date this BOM is intended to take effect. DRAFT BOMs may "
            "have a future date; ACTIVE/SUPERSEDED BOMs typically have a "
            "past or current date. Workflow validation lives in clean()."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    class Meta:
        verbose_name = "BOM"
        verbose_name_plural = "BOMs"
        # Most-recent first within a product is the natural reading order.
        ordering = ("finished_product", "-effective_from", "-version")
        constraints = [
            # Version label is unique per (organization, finished_product).
            # Keeps the "v2.1" label unambiguous within a product's history.
            models.UniqueConstraint(
                fields=("organization", "finished_product", "version"),
                name="bom_uniq_org_product_version",
            ),
            # AT MOST ONE ACTIVE BOM per finished_product per organization.
            # Postgres partial unique index — same pattern used in M3 step 2
            # for SupplierProduct's product/raw_material XOR uniqueness.
            # Without the WHERE clause, every DRAFT and SUPERSEDED row would
            # collide on (organization, finished_product), which is wrong.
            models.UniqueConstraint(
                fields=("organization", "finished_product"),
                condition=models.Q(status="ACTIVE"),
                name="bom_uniq_active_per_product",
            ),
        ]
        indexes = [
            # Lookup path: "what's the active BOM for this product?" — the
            # primary query the manufactured-product pricing strategy will run.
            models.Index(
                fields=("organization", "finished_product", "status"),
                name="bom_org_product_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"BOM {self.version} for {self.finished_product} ({self.status})"

    def clean(self) -> None:
        """Workflow-level validation.

        DB-level constraints handle the hard data-integrity invariants
        (uniqueness, FK integrity, exactly-one-ACTIVE). This method
        handles the softer workflow rules where Postgres-side enforcement
        would be overkill.
        """
        super().clean()
        errors: dict[str, list[str]] = {}

        # ACTIVE and SUPERSEDED BOMs should not have an effective_from in
        # the future — that would mean "this is the current spec but it
        # hasn't started yet," which contradicts the lifecycle.
        # DRAFT is allowed to have a future date (planning future revisions).
        if self.effective_from is not None and self.status in (
            self.Status.ACTIVE,
            self.Status.SUPERSEDED,
        ):
            from django.utils import timezone

            today = timezone.localdate()
            if self.effective_from > today:
                errors.setdefault("effective_from", []).append(
                    f"{self.status} BOMs cannot have an effective_from in "
                    f"the future (got {self.effective_from}; today is {today})."
                )

        if errors:
            raise ValidationError(errors)


class BOMLine(TenantModel):
    """A single material requirement within a BOM.

    Dual-quantity design (per design choice B5):
      - `quantity` + `unit_of_measure`: the human-readable specification
        ("use 3 KG of this steel"). Documents what to physically use.
      - `cost_basis_quantity`: the same physical amount expressed in the
        RawMaterial's catalog UoM (e.g. "= 0.25 M2 of steel"). Pricing math
        uses ONLY this field; conversion is the user's responsibility at
        entry time.

    Pricing formula (§13.1): manufactured Product cost roll-up =
        sum(BOMLine.cost_basis_quantity × BOMLine.cost_reference)

    `cost_reference` snapshot lifecycle (lives in the service layer, not
    here):
      - While parent BOM is DRAFT: cost_reference may track
        RawMaterial.current_cost (re-set on each save, or via a refresh
        action — TBD in step 4).
      - On parent BOM activation: cost_reference is frozen.
      - For SUPERSEDED BOMs: cost_reference remains frozen at the value
        captured during ACTIVE.

    The model itself doesn't enforce this lifecycle — it just stores the
    field. The service layer (M3 step 4) will enforce write rules based
    on parent.status.
    """

    bom = models.ForeignKey(
        "catalog_manufacturing.BOM",
        # CASCADE: BOMLines are intrinsic to a BOM, not independent records.
        # Deleting a BOM removes all its lines.
        on_delete=models.CASCADE,
        related_name="lines",
    )
    raw_material = models.ForeignKey(
        "catalog_materials.RawMaterial",
        # PROTECT: a RawMaterial referenced by ANY BOMLine (even in a
        # SUPERSEDED BOM) cannot be deleted. Historical pricing records
        # require the material data to remain intact.
        on_delete=models.PROTECT,
        related_name="bom_lines",
    )
    quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=(
            "Display quantity in `unit_of_measure`. Documents what to "
            "physically use. NOT used in pricing math — see "
            "`cost_basis_quantity` for that."
        ),
    )
    # Reuses the enum from RawMaterial. Per design choice (d): sharing the
    # enum keeps the domain consistent and makes "is this UoM valid?" a
    # single source-of-truth check.
    unit_of_measure = models.CharField(
        max_length=10,
        choices=RawMaterial.UnitOfMeasure.choices,
        help_text="Display unit. Need not match the RawMaterial's catalog UoM.",
    )
    cost_basis_quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=(
            "Same physical amount as `quantity`, but expressed in the "
            "RawMaterial's catalog UoM. THIS is the field pricing math uses. "
            "User does the conversion at entry time."
        ),
    )
    cost_reference = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=(
            "Per-RawMaterial-catalog-unit cost reference. Tracks "
            "RawMaterial.current_cost while the BOM is DRAFT; frozen on "
            "ACTIVE transition. Service-layer responsibility."
        ),
    )

    class Meta:
        verbose_name = "BOM line"
        verbose_name_plural = "BOM lines"
        # Within a BOM, lines order by raw material name for predictable display.
        ordering = ("bom", "raw_material__name")
        constraints = [
            # Each raw material appears at most once per BOM. If a BOM needs
            # the same material in two contexts (e.g. "steel for frame" and
            # "steel for legs"), the user combines them into one line OR
            # we revisit this constraint with a "purpose"/"position" field.
            # Single-line per material is the simpler default.
            models.UniqueConstraint(
                fields=("bom", "raw_material"),
                name="bom_line_uniq_bom_material",
            ),
        ]
        indexes = [
            # Lookup path: "list all lines for this BOM," in display order.
            models.Index(
                fields=("organization", "bom"),
                name="bom_line_org_bom_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} {self.unit_of_measure} of " f"{self.raw_material.name}"
