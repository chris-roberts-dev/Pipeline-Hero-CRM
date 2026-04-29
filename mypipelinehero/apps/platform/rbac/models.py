"""
RBAC models.

Spec §10 authorizes actions via:
  - system-defined **Capabilities** (global; platform-controlled)
  - organization-scoped **Roles** grouping capabilities
  - per-membership **Grants** that add or remove individual capabilities

The evaluator (spec §10.2) runs in a separate module; this file defines
data only. No business logic on models beyond constraints and natural
keys.

Tenancy posture:
  - Capability: GLOBAL — NOT a TenantModel. All orgs share the system
    capability codes. Tenants can't create their own codes in v1 per §10.4.
  - Role: TENANT-SCOPED. Each org has its own copies (including copies of
    the system-defined default roles).
  - RoleCapability: TENANT-SCOPED via its Role parent. The link model also
    carries an `organization` FK so the tenant-manager coverage test still
    passes and queries stay org-safe.
  - MembershipCapabilityGrant: TENANT-SCOPED. Attached to a Membership.

Why `is_system` on Role?
  §10.4 says "tenants may not modify the seeded default roles (those are
  read-only templates). Tenants may modify role assignments for their own
  members freely." The flag is the marker that makes "this role is a
  template, don't mutate it" enforceable at the service layer.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.tenancy.models import TenantModel


class Capability(models.Model):
    """A system-defined permission code.

    Capabilities are platform-controlled. Tenants may assign capabilities to
    roles and members but may NOT create new capability codes (spec §10.3).
    Codes follow the pattern `{domain}.{resource}.{action}` and are seeded
    via a data migration; this model exists as the FK target for Role and
    Grant rows.

    Not a TenantModel — capabilities are global.
    """

    # The code is the stable public identifier. Using a CharField primary-key
    # would make joins slightly cheaper but introduces foot-guns if a code
    # ever needs renaming — keep the synthetic id and make `code` unique.
    code = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        help_text=_(
            "Capability code, e.g. 'leads.view'. Follows {domain}.{resource}.{action}."
        ),
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    # Grouping for UI and display. Matches the top-level headings in
    # spec §10.3 (leads, quotes, clients, orders, catalog, workorders, ...).
    domain = models.CharField(max_length=40, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("capability")
        verbose_name_plural = _("capabilities")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(TenantModel):
    """A named collection of capabilities, scoped to one organization.

    Default roles (Owner, Org Admin, Regional/Market/Location Manager,
    Sales Staff, Service Staff, Production Staff, Viewer per §10.4) are
    seeded per-org at organization creation time. Tenants may create
    additional custom roles but may NOT modify the system-defined ones.
    """

    # `organization`, `created_at`, `updated_at` come from TenantModel.

    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    # Marks a role as a platform-defined template. Enforcement ("tenants
    # may not modify default roles") lives in the service layer — the
    # model itself just stores the flag. Services check this before
    # allowing edits or capability-assignment changes.
    is_system = models.BooleanField(
        default=False,
        help_text=_("True for platform-seeded default roles. Read-only to tenants."),
    )

    # `system_key` uniquely identifies a system-role template across all
    # organizations. This is how we look up "the Sales Staff role for org X"
    # without hard-coding role names. Null on tenant-created custom roles.
    # A new enum for system keys keeps the space bounded.
    class SystemKey(models.TextChoices):
        OWNER = "OWNER", _("Owner")
        ORG_ADMIN = "ORG_ADMIN", _("Org Admin")
        REGIONAL_MANAGER = "REGIONAL_MANAGER", _("Regional Manager")
        MARKET_MANAGER = "MARKET_MANAGER", _("Market Manager")
        LOCATION_MANAGER = "LOCATION_MANAGER", _("Location Manager")
        SALES_STAFF = "SALES_STAFF", _("Sales Staff")
        SERVICE_STAFF = "SERVICE_STAFF", _("Service Staff")
        PRODUCTION_STAFF = "PRODUCTION_STAFF", _("Production Staff")
        VIEWER = "VIEWER", _("Viewer")

    system_key = models.CharField(
        max_length=32,
        choices=SystemKey.choices,
        blank=True,
        null=True,
        help_text=_(
            "Identifies the default-role template. Null on tenant-custom roles."
        ),
    )

    capabilities = models.ManyToManyField(
        Capability,
        through="RoleCapability",
        related_name="roles",
    )

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["organization__name", "name"]
        constraints = [
            # Role name is unique within an org. Two different orgs can
            # each have a "Sales Staff" role — that's expected.
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="role_org_name_unique",
            ),
            # At most one system-default role per (org, system_key). This
            # prevents accidentally seeding "Sales Staff" twice for one org
            # if the seed service runs more than once. Partial constraint:
            # only rows where system_key is non-null are enforced.
            models.UniqueConstraint(
                fields=["organization", "system_key"],
                condition=models.Q(system_key__isnull=False),
                name="role_org_system_key_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization.slug})"


class RoleCapability(TenantModel):
    """Through-model linking a Role to a Capability.

    We use an explicit through-model rather than Django's implicit M2M
    so we can carry the `organization` FK (required by TenancyManager
    coverage) and add metadata if we ever need it (e.g. "who granted this
    capability to this role, when").
    """

    # `organization`, `created_at`, `updated_at` come from TenantModel.

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_capabilities"
    )
    capability = models.ForeignKey(
        Capability,
        on_delete=models.PROTECT,  # capabilities are system data; never delete
        related_name="role_assignments",
    )

    class Meta:
        verbose_name = _("role capability")
        verbose_name_plural = _("role capabilities")
        constraints = [
            models.UniqueConstraint(
                fields=["role", "capability"],
                name="role_capability_unique",
            ),
        ]
        indexes = [
            # Fast "what capabilities does this role have?" lookup —
            # used by the permission evaluator on every request.
            models.Index(
                fields=["role", "capability"],
                name="role_capability_lookup_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role.name} has {self.capability.code}"


class MembershipRole(TenantModel):
    """Assignment of a Role to a Membership.

    Spec §10.2 step 4: capability evaluation walks the membership's roles
    and unions their capability sets. This through table is the link.

    Why an explicit through table (not Membership.roles M2M)?
      - Carries the `organization` FK so the TenantManager coverage test
        passes and tenant queries stay org-safe.
      - Future-proofs for assignment metadata (assigned_by, assigned_at,
        expires_at — not needed today, but the spec hints at temporary
        role grants in the manager UI section).
      - Lets us index (membership, role) for fast role-list lookups
        during permission evaluation.

    A membership can have multiple roles, and a role can be assigned to
    multiple memberships within its organization. Cross-organization
    assignments are blocked by the FK constraint pattern (both sides
    carry the same `organization`) plus a clean check at the service
    layer.
    """

    # `organization`, `created_at`, `updated_at` come from TenantModel.

    membership = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,  # don't allow deleting an in-use role
        related_name="membership_assignments",
    )

    class Meta:
        verbose_name = _("membership role assignment")
        verbose_name_plural = _("membership role assignments")
        ordering = ["-created_at"]
        constraints = [
            # A role assignment is unique per (membership, role). Two
            # assignments of the same role to the same membership would
            # have no semantic difference and would just add noise.
            models.UniqueConstraint(
                fields=["membership", "role"],
                name="membership_role_unique",
            ),
        ]
        indexes = [
            # Evaluator hotspot: "all roles for this membership".
            models.Index(
                fields=["membership"],
                name="mbr_role_membership_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.membership} → {self.role.name}"


class MembershipCapabilityGrant(TenantModel):
    """A per-membership capability override.

    Spec §10.2 step 5: GRANT overrides ADD capabilities beyond the role
    set; DENY overrides REMOVE capabilities that would otherwise be granted
    by a role. DENY takes precedence over role grants.

    Use cases:
      - A Sales Staff member with a temporary grant of `quotes.approve`
        for a specific project (then revoked).
      - A Regional Manager with a DENY on `billing.invoice.void` because
        a recent incident requires stricter separation of duties.
    """

    class GrantType(models.TextChoices):
        GRANT = "GRANT", _("Grant")
        DENY = "DENY", _("Deny")

    # `organization`, `created_at`, `updated_at` come from TenantModel.

    membership = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.CASCADE,
        related_name="capability_grants",
    )
    capability = models.ForeignKey(
        Capability,
        on_delete=models.PROTECT,
        related_name="membership_grants",
    )
    grant_type = models.CharField(
        max_length=8,
        choices=GrantType.choices,
        help_text=_(
            "GRANT adds the capability; DENY removes it (overrides role grants)."
        ),
    )

    # Free-form rationale, shown in audit events and UI. Not required but
    # strongly encouraged — capability overrides are high-trust changes.
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("capability grant")
        verbose_name_plural = _("capability grants")
        ordering = ["-created_at"]
        constraints = [
            # At most one grant row per (membership, capability, grant_type).
            # We allow a membership to have a GRANT and DENY on the same
            # capability ONLY if paired with distinct grant_type values —
            # the evaluator will apply DENY precedence anyway, but duplicate
            # rows of the SAME type are confusing and prevented here.
            models.UniqueConstraint(
                fields=["membership", "capability", "grant_type"],
                name="membership_capability_grant_unique",
            ),
        ]
        indexes = [
            # Evaluator hotspot: "all grants for this membership, by type".
            models.Index(
                fields=["membership", "grant_type"],
                name="mbr_grant_type_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.grant_type} {self.capability.code} -> {self.membership}"


class MembershipScopeAssignment(TenantModel):
    """Operating-scope assignment for a membership.

    Per spec §7.2A line 414, a membership may have ONE OR MORE scope
    assignments. Each assignment scopes the membership to either a
    Region, a Market, or a Location — exactly one of the three.

    Why three nullable FKs + CHECK constraint instead of GenericForeignKey?
      - Type-safe: Django ORM knows the target model; queries can join.
      - Queryable without GFK overhead: filtering by `region__name` is
        a normal lookup; with GFK it's two queries minimum.
      - Self-documenting in admin and database introspection.
      - Constraint enforces "exactly one" at the DB layer, so partial-write
        bugs surface immediately rather than silently producing
        inconsistent state.

    "Within scope" semantics (evaluator step 8):
      - A REGION assignment includes that region's Markets and Locations.
      - A MARKET assignment includes that market's Locations only.
      - A LOCATION assignment is leaf-level — only that one location.
      - A membership with multiple assignments has scope = union of all.
    """

    # `organization`, `created_at`, `updated_at` come from TenantModel.

    membership = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.CASCADE,
        related_name="scope_assignments",
    )

    # Exactly one of these three is non-null per row, enforced by the
    # CHECK constraint below. PROTECT on the targets prevents deleting
    # a Region/Market/Location while it's still scoping someone — admin
    # has to remove the assignment first (a deliberate friction point;
    # accidental scope-deletion would silently broaden access).
    region = models.ForeignKey(
        "locations.Region",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scope_assignments",
    )
    market = models.ForeignKey(
        "locations.Market",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scope_assignments",
    )
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scope_assignments",
    )

    # Free-form rationale, mirrored from MembershipCapabilityGrant. Useful
    # in audit and admin — "why was Alice given the Eastern Region?"
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("membership scope assignment")
        verbose_name_plural = _("membership scope assignments")
        ordering = ["-created_at"]
        constraints = [
            # Exactly one of region/market/location must be non-null. We use
            # a Q-expression rather than raw SQL so it portable across DBs.
            # `condition=` is the Django 5.1+ name; the old `check=` is
            # still supported but deprecated.
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(region__isnull=False)
                        & models.Q(market__isnull=True)
                        & models.Q(location__isnull=True)
                    )
                    | (
                        models.Q(region__isnull=True)
                        & models.Q(market__isnull=False)
                        & models.Q(location__isnull=True)
                    )
                    | (
                        models.Q(region__isnull=True)
                        & models.Q(market__isnull=True)
                        & models.Q(location__isnull=False)
                    )
                ),
                name="scope_assignment_exactly_one_target",
            ),
            # No duplicate assignments — same membership shouldn't have the
            # same Region (or Market, or Location) assigned twice.
            models.UniqueConstraint(
                fields=["membership", "region"],
                condition=models.Q(region__isnull=False),
                name="scope_assignment_no_dup_region",
            ),
            models.UniqueConstraint(
                fields=["membership", "market"],
                condition=models.Q(market__isnull=False),
                name="scope_assignment_no_dup_market",
            ),
            models.UniqueConstraint(
                fields=["membership", "location"],
                condition=models.Q(location__isnull=False),
                name="scope_assignment_no_dup_location",
            ),
        ]
        indexes = [
            models.Index(
                fields=["membership"],
                name="mbr_scope_membership_idx",
            ),
        ]

    @property
    def kind(self) -> str:
        """Return 'region', 'market', or 'location' — whichever target is set."""
        if self.region_id is not None:
            return "region"
        if self.market_id is not None:
            return "market"
        if self.location_id is not None:
            return "location"
        # Should be unreachable thanks to the CHECK constraint, but
        # belt-and-braces.
        return "unknown"

    @property
    def target(self):
        """Return the single non-null target object."""
        return self.region or self.market or self.location

    def __str__(self) -> str:
        return f"{self.membership} scoped to {self.kind}: {self.target}"
