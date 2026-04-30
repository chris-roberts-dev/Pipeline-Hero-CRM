"""
Supplier and SupplierProduct models.

Two models in this file:
  - Supplier: external party we buy from. First-class entity with a
    status workflow (ACTIVE/INACTIVE/SUSPENDED) — distinct from the simpler
    on/off `is_active` flag used by Service/Product/RawMaterial.
  - SupplierProduct: join row pairing a Supplier with EITHER a Product
    OR a RawMaterial (never both, never neither). Carries the
    per-supplier sku, default_cost, and lead time used by the resale
    pricing strategy (§13.1).

Polymorphism choice: two nullable FKs (`product` and `raw_material`) with
a CHECK constraint enforcing exactly-one-non-null. Considered alternatives:
  - GenericForeignKey via contenttypes: schema-opaque, slow joins, makes
    the cross-app FK boundary invisible.
  - Two separate join tables: doubles the surface area of every query
    that wants "what does this supplier offer?" with no clear win.

The CHECK keeps the integrity guarantee in the schema where it's
reviewable. The two partial unique indexes prevent duplicate rows
within a single (supplier, product) or (supplier, raw_material) pair —
Postgres treats NULLs as distinct in a vanilla UNIQUE so we need partial
indexes scoped to each FK.

Index/constraint names use the `sup_` prefix and stay under Django's
30-char limit on index identifiers.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.decimal_precision import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.common.tenancy.models import TenantModel


class Supplier(TenantModel):
    """An external party we purchase products or raw materials from.

    Has a status workflow rather than a simple is_active boolean —
    SUSPENDED is operationally distinct from INACTIVE (e.g. a payment
    dispute that we expect to resolve, vs. a supplier we've permanently
    stopped using). Status drives whether the supplier can be selected
    in quote lines and whether new POs can be issued to them.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        # Temporarily blocked (dispute, paperwork issue, etc). Distinct
        # from INACTIVE because the operational expectation is recovery,
        # and reporting may want to see SUSPENDED suppliers separately.
        SUSPENDED = "SUSPENDED", "Suspended"

    name = models.CharField(
        max_length=200,
        help_text="Display name of the supplier; unique within an organization.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    # Contact fields (intentionally minimal flat set; richer modeling like
    # multiple contacts or address blocks is deferred until a real use case
    # demands it). All blank by default — many suppliers have only a few
    # of these populated.
    contact_name = models.CharField(max_length=200, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    website = models.URLField(blank=True, default="")

    class Meta:
        verbose_name = "supplier"
        verbose_name_plural = "suppliers"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "name"),
                name="sup_supplier_uniq_org_name",
            ),
        ]
        indexes = [
            # Browse path: list active suppliers for an org, alphabetically.
            # Status is the analog of is_active for this model.
            models.Index(
                fields=("organization", "status", "name"),
                name="sup_supplier_org_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class SupplierProduct(TenantModel):
    """A supplier's offering of either a Product (resale) or a RawMaterial.

    Polymorphism via two nullable FKs + CHECK. Exactly one of `product` or
    `raw_material` is populated; the CHECK enforces this at the database
    level so application bugs can't insert invalid rows.

    Per-supplier identifiers and pricing live here, not on Product /
    RawMaterial, because the *same* product may be sourced from multiple
    suppliers at different costs and SKUs. The default_cost field is the
    base input to the resale pricing strategy (§13.1: "Markup % over
    supplier cost").
    """

    supplier = models.ForeignKey(
        # Same-app reference: Supplier lives in this app.
        "catalog_suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="supplier_products",
    )
    # Cross-app FKs. Nullable because exactly one is populated per row.
    product = models.ForeignKey(
        "catalog_products.Product",
        on_delete=models.PROTECT,
        related_name="supplier_offerings",
        null=True,
        blank=True,
    )
    raw_material = models.ForeignKey(
        "catalog_materials.RawMaterial",
        on_delete=models.PROTECT,
        related_name="supplier_offerings",
        null=True,
        blank=True,
    )
    supplier_sku = models.CharField(
        max_length=64,
        help_text="The supplier's own SKU/code for this item.",
    )
    default_cost = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=(
            "Per-unit cost from this supplier. Base input to the resale "
            "pricing strategy. Zero allowed (unpriced placeholder); "
            "negative is rejected."
        ),
    )
    lead_time_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Typical lead time in days from order to delivery. NULL when "
            "unknown. Single field rather than min/max — if the project "
            "ever needs a range, that's an additive change."
        ),
    )

    class Meta:
        verbose_name = "supplier product"
        verbose_name_plural = "supplier products"
        ordering = ("supplier__name", "supplier_sku")
        constraints = [
            # Exactly one of product / raw_material must be non-null.
            # Two clauses: (product set, material null) OR (product null,
            # material set). Verified to enforce against both error cases:
            # both null and both set.
            models.CheckConstraint(
                condition=(
                    models.Q(product__isnull=False, raw_material__isnull=True)
                    | models.Q(product__isnull=True, raw_material__isnull=False)
                ),
                name="sup_sp_target_xor",
            ),
            # Partial unique indexes per target type. A given (supplier,
            # product) pair is unique; same for (supplier, raw_material).
            # Without `condition=`, a vanilla UNIQUE on (supplier, product)
            # would treat each NULL product as distinct, allowing infinite
            # rows for raw-material rows — a real data integrity hole.
            models.UniqueConstraint(
                fields=("supplier", "product"),
                condition=models.Q(product__isnull=False),
                name="sup_sp_uniq_supplier_product",
            ),
            models.UniqueConstraint(
                fields=("supplier", "raw_material"),
                condition=models.Q(raw_material__isnull=False),
                name="sup_sp_uniq_supplier_material",
            ),
        ]
        indexes = [
            # Lookup path: "what does this supplier offer?" Most common
            # query when rendering the supplier detail page.
            models.Index(
                fields=("organization", "supplier"),
                name="sup_sp_org_supplier_idx",
            ),
            # Reverse lookup: "who supplies this product?" Used by the
            # quote-line supplier picker.
            models.Index(
                fields=("organization", "product"),
                name="sup_sp_org_product_idx",
            ),
            models.Index(
                fields=("organization", "raw_material"),
                name="sup_sp_org_material_idx",
            ),
        ]

    def __str__(self) -> str:
        target = self.product or self.raw_material
        return f"{self.supplier.name} → {target} @ {self.default_cost}"

    @property
    def target(self):
        """The Product or RawMaterial this offering points to.

        Convenience for code that doesn't care which side is populated;
        the CHECK constraint guarantees exactly one is non-null.
        """
        return self.product or self.raw_material
