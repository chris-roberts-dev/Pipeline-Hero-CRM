"""
Service and ServiceCategory models.

Two models in this file:
  - ServiceCategory: org-scoped grouping for services
  - Service: work-performed-for-client; flat catalog price (v1 pricing input)

Both inherit `TenantModel` from apps.common.tenancy.models, which provides:
  - organization FK (PROTECT, related_name="+")
  - created_at / updated_at
  - `objects = TenantManager()` with `.for_org(org)` for queryset scoping

Per the abstract base's contract, each model below sets its own
`Meta.ordering` rather than relying on the database. Per spec §25.3 / §25.4,
indexes and constraints are pinned to (organization, code) because that's
how the catalog browse and lookup paths query.

Index/constraint names use the `svc_` prefix to namespace within the
services app and stay under PostgreSQL's identifier limit (Django enforces
30 chars on index names specifically).
"""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.decimal_precision import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.common.tenancy.models import TenantModel


class ServiceCategory(TenantModel):
    """Tenant-scoped grouping for Services.

    Categories are flat — no parent/child hierarchy in v1. If we ever need
    a tree, it's an additive change (add `parent = TreeForeignKey(...)`).
    """

    code = models.CharField(
        max_length=64,
        help_text="Short stable identifier, unique within an organization.",
    )
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Soft-disable flag. Inactive categories are hidden from the "
            "quote-line picker but retained for historical references."
        ),
    )

    class Meta:
        verbose_name = "service category"
        verbose_name_plural = "service categories"
        # Explicit ordering — the abstract base's Meta deliberately leaves
        # this unset and warns against the implicit ORDER BY id default.
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code"),
                name="svc_svccat_uniq_org_code",
            ),
        ]
        indexes = [
            # Browse path: list active categories for an org, ordered by name.
            models.Index(
                fields=("organization", "is_active", "name"),
                name="svc_svccat_org_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Service(TenantModel):
    """A service the organization sells — the work-performed-for-client side
    of the catalog.

    Per spec §13.1 line 1126, services use a *flat catalog price* in v1:
    the pricing engine reads `catalog_price` directly from this row as the
    base unit price, then the shared override/discount layer applies on top.
    Future labor-based service formulas (§13.4) will swap the strategy
    without changing this field.
    """

    category = models.ForeignKey(
        # Same-app reference: ServiceCategory lives in this same app
        # (label "catalog_services").
        "catalog_services.ServiceCategory",
        on_delete=models.PROTECT,
        related_name="services",
        help_text="A category cannot be deleted while services reference it.",
    )
    code = models.CharField(
        max_length=64,
        help_text="Service code, unique within an organization.",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    catalog_price = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        # Negative catalog prices are nonsensical at the catalog level.
        # Negative MARKUP at zero is allowed in pricing rules per spec
        # §13.1 ("Negative markup: Allowed at zero; negative blocked at
        # PricingRule validation layer") — that's a separate concern handled
        # at the rule layer, not here.
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Flat unit price used as the v1 base for service line pricing.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Soft-disable flag. Inactive services are hidden from the "
            "quote-line picker but retained for historical references."
        ),
    )

    class Meta:
        verbose_name = "service"
        verbose_name_plural = "services"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code"),
                name="svc_service_uniq_org_code",
            ),
        ]
        indexes = [
            # Browse path mirrors ServiceCategory.
            models.Index(
                fields=("organization", "is_active", "name"),
                name="svc_service_org_active_idx",
            ),
            # Category drilldown: "show me active services in this category".
            models.Index(
                fields=("organization", "category", "is_active"),
                name="svc_service_org_cat_act_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name
