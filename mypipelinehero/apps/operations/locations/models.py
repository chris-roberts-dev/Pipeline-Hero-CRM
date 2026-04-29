"""
Operating-scope geography models.

Spec §7.2A defines a three-level hierarchy: Region → Market → Location.
Every level is organization-scoped (TenantModel). Markets belong to exactly
one Region; Locations belong to exactly one Market.

These models exist purely as scope anchors. Other domain models (Leads,
Quotes, Clients, etc.) reference Locations directly or transitively to
participate in scoped access.

The `get_scope_location()` protocol:
  Models that participate in operating-scope evaluation implement
  `get_scope_location() -> Optional[Location]`. The permission evaluator
  calls this to determine which scope a target falls under. Models with
  no scope (Catalog, Roles, etc.) simply don't implement the method —
  the evaluator treats their scope step as a pass-through.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.tenancy.models import TenantModel


class Region(TenantModel):
    """Top-level operating scope within an organization.

    Names are unique within an org. A Manager assigned to this Region sees
    every Market and Location within it.
    """

    name = models.CharField(max_length=120)
    code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_(
            "Optional short code for reports and UI. Unique within org if set."
        ),
    )

    class Meta:
        verbose_name = _("region")
        verbose_name_plural = _("regions")
        ordering = ["organization__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="region_org_name_unique",
            ),
            # Code is unique-within-org only when present (partial index).
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=~models.Q(code=""),
                name="region_org_code_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization.slug})"

    def get_scope_location(self) -> Location | None:
        """Regions are scope anchors, not data targets — they have no
        own location. Returning None means 'this object is the scope
        boundary itself'; the evaluator handles that case correctly."""
        return None


class Market(TenantModel):
    """Mid-level operating scope under a Region."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,  # don't allow orphaning markets
        related_name="markets",
    )

    class Meta:
        verbose_name = _("market")
        verbose_name_plural = _("markets")
        ordering = ["region__name", "name"]
        constraints = [
            # Names are unique within a region (a "Downtown" market in two
            # different regions is fine; two "Downtown"s in the same region
            # are not).
            models.UniqueConstraint(
                fields=["region", "name"],
                name="market_region_name_unique",
            ),
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=~models.Q(code=""),
                name="market_org_code_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} (Region: {self.region.name})"

    def get_scope_location(self) -> Location | None:
        return None


class Location(TenantModel):
    """Leaf-level operating scope. Most domain objects resolve to a Location
    when participating in scoped access."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)
    market = models.ForeignKey(
        Market,
        on_delete=models.PROTECT,
        related_name="locations",
    )

    # Free-form address / metadata. Kept as a single text field for v1 —
    # structured address breakdown can wait until somewhere uses it.
    address = models.TextField(blank=True)

    class Meta:
        verbose_name = _("location")
        verbose_name_plural = _("locations")
        ordering = ["market__region__name", "market__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["market", "name"],
                name="location_market_name_unique",
            ),
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=~models.Q(code=""),
                name="location_org_code_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.market.region.name} / {self.market.name})"

    def get_scope_location(self) -> Location | None:
        """A Location's scope-location IS itself."""
        return self

    @property
    def region(self) -> Region:
        """Convenience accessor — saves a Market round-trip in templates
        and admin."""
        return self.market.region
