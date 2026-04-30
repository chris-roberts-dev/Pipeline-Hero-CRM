"""
Central admin registrations for the platform console.

All ModelAdmin classes for M1+M2 models live here rather than scattered
across each app's admin.py. Rationale:
  - Single place to read the entire console's surface
  - Easier to audit "what's exposed in admin?" at a glance
  - Consistent pattern: every app's models have their admin defined here
  - No risk of accidentally registering against `admin.site` (the global)
    instead of our `console_site`

Conventions:
  - `list_display`, `list_filter`, `search_fields` configured per model
  - `list_select_related` set wherever the list view dereferences FKs to
    avoid N+1 queries
  - `readonly_fields` for audit/computed fields (created_at, updated_at, etc.)
  - For tenant-scoped models, `list_filter` includes `organization`
  - For read-only models (audit, impersonation sessions), permission
    methods return False to forbid mutations

Permission posture (v1):
  - Default Django permissions check `is_staff` and Permission grants
  - Today, only superusers have any practical access; the platform-staff
    role with proper Permission grants ships in a future milestone
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.catalog.manufacturing.models import BOM, BOMLine
from apps.catalog.materials.models import RawMaterial
from apps.catalog.pricing.models import PricingRule, PricingSnapshot
from apps.catalog.products.models import Product
from apps.catalog.services.models import Service, ServiceCategory
from apps.catalog.suppliers.models import Supplier, SupplierProduct
from apps.operations.locations.models import Location, Market, Region
from apps.platform.accounts.models import User
from apps.platform.audit.models import AuditEvent
from apps.platform.console.sites import console_site
from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.models import (
    Capability,
    MembershipCapabilityGrant,
    MembershipRole,
    MembershipScopeAssignment,
    Role,
    RoleCapability,
)
from apps.platform.support.models import ImpersonationSession

# ===========================================================================
# Mixins
# ===========================================================================


class ReadOnlyAdmin(admin.ModelAdmin):
    """Mixin for models that should be view-only in admin.

    Used for AuditEvent and ImpersonationSession — these are append-only
    historical records that should never be hand-edited via admin.
    Allowing edits would let an admin rewrite the audit log to cover their
    tracks, which defeats the entire point of audit.

    Permissions:
      - View: allowed (handled by the standard `view_<model>` Django permission)
      - Add / Change / Delete: forbidden regardless of Django permissions
    """

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TenantScopedAdmin(admin.ModelAdmin):
    """Mixin for tenant-scoped models. Adds organization filter and select_related."""

    list_select_related = ("organization",)

    def get_list_filter(self, request):
        # Prepend the organization filter so it's the first thing in the
        # sidebar — usually what the admin wants to narrow by first.
        existing = list(super().get_list_filter(request))
        if "organization" not in existing:
            existing.insert(0, "organization")
        return existing


# ===========================================================================
# Platform: User
# ===========================================================================


@admin.register(User, site=console_site)
class UserAdmin(DjangoUserAdmin):
    """Custom UserAdmin that works with our email-as-username user model.

    Django's bundled UserAdmin assumes a `username` field. Ours has none —
    email is the USERNAME_FIELD. We override the form/fieldset config to
    drop the username assumption and surface the fields we actually have.
    """

    # Email instead of username everywhere.
    ordering = ("email",)
    list_display = ("email", "is_active", "is_staff", "is_superuser", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email",)
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


# ===========================================================================
# Platform: Organization
# ===========================================================================


@admin.register(Organization, site=console_site)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)

    def save_model(self, request, obj, form, change):
        """Route new-organization creation through the service layer.

        Django's default `save_model` would call `obj.save()` directly,
        bypassing `create_organization()` — which means no default roles
        get seeded and no ORGANIZATION_CREATED audit event gets emitted.
        For existing objects (edits to name/slug/status), the default
        path is fine — those don't need re-seeding.

        On creation we:
          - Pull the cleaned form values rather than calling the service
            with `obj` directly (the service builds its own instance and
            runs full_clean before saving)
          - Pass the request user as the creator so the audit attribution
            is correct
          - Catch our domain ValidationError and surface as a form error
            via Django's standard messaging, so the admin re-renders the
            form rather than 500ing
        """
        from apps.common.services import ValidationError as DomainValidationError
        from apps.platform.organizations.services import create_organization

        if change:
            # Existing object — default save is fine for name/slug/status
            # edits. Roles already exist; we don't want to re-seed.
            super().save_model(request, obj, form, change)
            return

        # New object. Build the service-layer kwargs from the unsaved
        # instance. The service does its own validation and saves.
        try:
            new_org = create_organization(
                name=obj.name,
                slug=obj.slug,
                created_by=request.user,
                # Pass through any non-default status the admin set.
                # Defaulting handled by the model field if not provided.
                status=obj.status,
            )
        except DomainValidationError as exc:
            # Convert to Django's ValidationError so the admin re-renders
            # the form with the error visible instead of returning a 500.
            # Django's admin _changeform_view catches this and surfaces it
            # via the form's non-field errors. We deliberately do NOT also
            # call messages.error() — it would duplicate the message AND
            # require a fully-middleware-processed request (with _messages
            # attached), which makes save_model harder to test in isolation.
            from django.core.exceptions import ValidationError as DjValidationError

            raise DjValidationError(str(exc)) from exc

        # The service created and saved a new instance. Wire its PK back
        # into `obj` so Django's response_add() can build the redirect
        # URL (it reads obj.pk for the "saved successfully" message and
        # the "view" link).
        obj.pk = new_org.pk
        obj.id = new_org.pk
        # Refresh other server-set fields from the saved row.
        obj.created_at = new_org.created_at
        obj.updated_at = new_org.updated_at


# ===========================================================================
# Platform: Membership
# ===========================================================================


@admin.register(Membership, site=console_site)
class MembershipAdmin(TenantScopedAdmin):
    list_display = ("user", "organization", "status", "is_default", "created_at")
    list_filter = ("status", "is_default")
    search_fields = ("user__email", "organization__name", "organization__slug")
    list_select_related = ("user", "organization")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "organization")
    ordering = ("organization__name", "user__email")


# ===========================================================================
# Platform: RBAC
# ===========================================================================


@admin.register(Capability, site=console_site)
class CapabilityAdmin(ReadOnlyAdmin):
    """Capabilities are platform-defined and seeded by migration. The admin
    surface is read-only — adding new capability codes through the admin
    would bypass the registry's import-time validation."""

    list_display = ("code", "name", "domain")
    list_filter = ("domain",)
    search_fields = ("code", "name", "description")
    ordering = ("domain", "code")


@admin.register(Role, site=console_site)
class RoleAdmin(TenantScopedAdmin):
    list_display = (
        "name",
        "organization",
        "is_system",
        "system_key",
        "capability_count",
    )
    list_filter = ("is_system", "system_key")
    search_fields = ("name", "organization__name", "description")
    list_select_related = ("organization",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organization",)
    ordering = ("organization__name", "name")

    @admin.display(description="Capabilities")
    def capability_count(self, obj: Role) -> int:
        # Cheap COUNT() per row in the changelist. For a few hundred roles
        # this is fine; if it ever scales, switch to annotation.
        return obj.role_capabilities.count()


@admin.register(RoleCapability, site=console_site)
class RoleCapabilityAdmin(TenantScopedAdmin):
    """Role↔Capability assignments. Listed mainly for diagnostic visibility;
    capability sets on system roles are managed through the seeding
    service rather than direct admin edits."""

    list_display = ("role", "capability", "organization", "created_at")
    search_fields = ("role__name", "capability__code")
    list_select_related = ("role", "capability", "organization")
    raw_id_fields = ("role", "capability", "organization")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MembershipRole, site=console_site)
class MembershipRoleAdmin(TenantScopedAdmin):
    list_display = ("membership", "role", "organization", "created_at")
    search_fields = ("membership__user__email", "role__name", "organization__name")
    list_select_related = (
        "membership__user",
        "membership__organization",
        "role",
        "organization",
    )
    raw_id_fields = ("membership", "role", "organization")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MembershipCapabilityGrant, site=console_site)
class MembershipCapabilityGrantAdmin(TenantScopedAdmin):
    list_display = (
        "membership",
        "capability",
        "grant_type",
        "organization",
        "created_at",
    )
    list_filter = ("grant_type",)
    search_fields = (
        "membership__user__email",
        "capability__code",
        "reason",
    )
    list_select_related = ("membership__user", "capability", "organization")
    raw_id_fields = ("membership", "capability", "organization")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MembershipScopeAssignment, site=console_site)
class MembershipScopeAssignmentAdmin(TenantScopedAdmin):
    list_display = (
        "membership",
        "kind",
        "target_label",
        "organization",
        "created_at",
    )
    search_fields = (
        "membership__user__email",
        "region__name",
        "market__name",
        "location__name",
    )
    list_select_related = (
        "membership__user",
        "region",
        "market",
        "location",
        "organization",
    )
    raw_id_fields = (
        "membership",
        "region",
        "market",
        "location",
        "organization",
    )
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Target")
    def target_label(self, obj: MembershipScopeAssignment) -> str:
        return str(obj.target) if obj.target else "—"


# ===========================================================================
# Platform: Audit
# ===========================================================================


@admin.register(AuditEvent, site=console_site)
class AuditEventAdmin(ReadOnlyAdmin):
    """Audit events are append-only — admin is view-only by design.

    The UI lets you filter by event_type, user, and organization. Full-text
    search covers the metadata JSON via Django's search support (substring
    match against a casted string). For deep forensic queries, drop into
    the Django shell or a SQL client.
    """

    list_display = (
        "created_at",
        "event_type",
        "actor_user",
        "on_behalf_of_user",
        "organization",
        "target_model_label",
        "target_pk",
    )
    list_filter = ("event_type",)
    search_fields = (
        "event_type",
        "actor_user__email",
        "on_behalf_of_user__email",
        "organization__name",
        "organization__slug",
        "target_model_label",
        "target_pk",
        "ip_address",
    )
    list_select_related = ("actor_user", "on_behalf_of_user", "organization")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


# ===========================================================================
# Platform: Impersonation
# ===========================================================================


@admin.register(ImpersonationSession, site=console_site)
class ImpersonationSessionAdmin(ReadOnlyAdmin):
    """Impersonation sessions are also view-only — same rationale as audit.

    Sessions are started via the dedicated `start_impersonation` admin
    view (linked from the changelist) and ended via the in-app banner.
    Direct edits through admin would let an attacker fabricate session
    history, defeating the audit trail.
    """

    list_display = (
        "started_at",
        "support_user",
        "target_user",
        "target_organization",
        "status_label",
        "ends_at",
        "ended_at",
    )
    list_filter = ()  # status is computed; no useful list_filter fields
    search_fields = (
        "support_user__email",
        "target_user__email",
        "target_organization__name",
        "target_organization__slug",
        "reason",
        "session_id",
    )
    list_select_related = (
        "support_user",
        "target_user",
        "target_organization",
    )
    date_hierarchy = "started_at"
    ordering = ("-started_at",)

    @admin.display(description="Status")
    def status_label(self, obj: ImpersonationSession) -> str:
        if obj.ended_at is not None:
            return format_html('<span style="color:#6b7280">ended</span>')
        if obj.is_active:
            return format_html(
                '<span style="color:#059669;font-weight:bold">active</span>'
            )
        # ended_at is None but ends_at has passed — expired.
        return format_html('<span style="color:#b45309">expired</span>')


# ===========================================================================
# Operations: Locations
# ===========================================================================


@admin.register(Region, site=console_site)
class RegionAdmin(TenantScopedAdmin):
    list_display = ("name", "code", "organization", "market_count")
    search_fields = ("name", "code", "organization__name")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organization",)
    ordering = ("organization__name", "name")

    @admin.display(description="Markets")
    def market_count(self, obj: Region) -> int:
        return obj.markets.count()


@admin.register(Market, site=console_site)
class MarketAdmin(TenantScopedAdmin):
    list_display = ("name", "code", "region", "organization", "location_count")
    search_fields = ("name", "code", "region__name", "organization__name")
    list_select_related = ("region", "organization")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("region", "organization")
    ordering = ("organization__name", "region__name", "name")

    @admin.display(description="Locations")
    def location_count(self, obj: Market) -> int:
        return obj.locations.count()


@admin.register(Location, site=console_site)
class LocationAdmin(TenantScopedAdmin):
    list_display = ("name", "code", "market", "region_label", "organization")
    search_fields = ("name", "code", "market__name", "organization__name")
    list_select_related = ("market__region", "organization")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("market", "organization")
    ordering = ("organization__name", "market__region__name", "market__name", "name")

    @admin.display(description="Region")
    def region_label(self, obj: Location) -> str:
        return obj.market.region.name


# ===========================================================================
# Catalog: Services
# ===========================================================================


@admin.register(ServiceCategory, site=console_site)
class ServiceCategoryAdmin(TenantScopedAdmin):
    list_display = ("name", "code", "is_active", "organization", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "organization__name")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("organization",)
    ordering = ("organization__name", "name")


@admin.register(Service, site=console_site)
class ServiceAdmin(TenantScopedAdmin):
    list_display = (
        "name",
        "code",
        "category",
        "catalog_price",
        "is_active",
        "organization",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description", "organization__name")
    # IMPORTANT: must include "organization" explicitly. The parent
    # TenantScopedAdmin sets list_select_related = ("organization",), but
    # subclassing replaces rather than extends — see comment in patch header.
    list_select_related = ("organization", "category")
    raw_id_fields = ("organization", "category")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "name")


# ===========================================================================
# Catalog: Products
# ===========================================================================


@admin.register(Product, site=console_site)
class ProductAdmin(TenantScopedAdmin):
    list_display = (
        "name",
        "sku",
        "product_type",
        "is_active",
        "organization",
        "created_at",
    )
    list_filter = ("product_type", "is_active")
    search_fields = ("sku", "name", "description", "organization__name")
    raw_id_fields = ("organization",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "name")


# ===========================================================================
# Catalog: Materials
# ===========================================================================


@admin.register(RawMaterial, site=console_site)
class RawMaterialAdmin(TenantScopedAdmin):
    list_display = (
        "name",
        "sku",
        "unit_of_measure",
        "current_cost",
        "is_active",
        "organization",
        "created_at",
    )
    list_filter = ("unit_of_measure", "is_active")
    search_fields = ("sku", "name", "organization__name")
    raw_id_fields = ("organization",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "name")


# ===========================================================================
# Catalog: Suppliers
# ===========================================================================


@admin.register(Supplier, site=console_site)
class SupplierAdmin(TenantScopedAdmin):
    list_display = (
        "name",
        "status",
        "contact_name",
        "email",
        "phone",
        "organization",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "name",
        "contact_name",
        "email",
        "phone",
        "organization__name",
    )
    raw_id_fields = ("organization",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "name")


@admin.register(SupplierProduct, site=console_site)
class SupplierProductAdmin(TenantScopedAdmin):
    list_display = (
        "supplier",
        "target_label",
        "supplier_sku",
        "default_cost",
        "lead_time_days",
        "organization",
    )
    list_filter = ("supplier", "lead_time_days")
    search_fields = (
        "supplier__name",
        "supplier_sku",
        "product__name",
        "product__sku",
        "raw_material__name",
        "raw_material__sku",
        "organization__name",
    )
    # IMPORTANT: include "organization" explicitly. The parent
    # TenantScopedAdmin sets list_select_related = ("organization",), but
    # subclassing replaces rather than extends.
    list_select_related = (
        "organization",
        "supplier",
        "product",
        "raw_material",
    )
    raw_id_fields = ("organization", "supplier", "product", "raw_material")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "supplier__name", "supplier_sku")

    @admin.display(description="Target", ordering="product__name")
    def target_label(self, obj: SupplierProduct) -> str:
        """Polymorphic target label for the changelist.

        Renders as "Product: Widget" or "Material: Steel Sheet" depending
        on which side of the SupplierProduct's product/raw_material XOR
        is populated. The CHECK constraint on the model guarantees exactly
        one is non-null, so the fallback "—" should be unreachable in
        valid data — but kept defensively in case of corrupted rows that
        somehow bypass the CHECK.
        """
        if obj.product_id is not None:
            return f"Product: {obj.product.name}"
        if obj.raw_material_id is not None:
            return f"Material: {obj.raw_material.name}"
        return "—"


# ===========================================================================
# Catalog: Manufacturing
# ===========================================================================


class BOMLineInline(admin.TabularInline):
    """Inline edit lines from the BOM detail page.

    Lines are intrinsic to a BOM (CASCADE on bom.delete), so editing in
    place is the natural UX rather than a separate top-level admin page
    for individual lines. Top-level BOMLine admin (registered below) is
    still useful for cross-BOM searches and audit lookups.
    """

    model = BOMLine
    extra = 0
    fields = (
        "raw_material",
        "quantity",
        "unit_of_measure",
        "cost_basis_quantity",
        "cost_reference",
    )
    raw_id_fields = ("raw_material",)


@admin.register(BOM, site=console_site)
class BOMAdmin(TenantScopedAdmin):
    list_display = (
        "version",
        "finished_product",
        "status",
        "effective_from",
        "organization",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "version",
        "finished_product__name",
        "finished_product__sku",
        "organization__name",
    )
    # IMPORTANT: include "organization" explicitly. TenantScopedAdmin sets
    # list_select_related = ("organization",) on the parent, and subclassing
    # replaces rather than extends.
    list_select_related = ("organization", "finished_product")
    raw_id_fields = ("organization", "finished_product")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "finished_product__name", "-effective_from")
    inlines = [BOMLineInline]


@admin.register(BOMLine, site=console_site)
class BOMLineAdmin(TenantScopedAdmin):
    """Top-level changelist for individual BOM lines.

    Useful for cross-BOM queries — "what BOMs use this raw material" and
    "what cost_reference values are stale" are both BOMLine-level questions
    that the inline-on-BOM view can't answer cleanly. The inline above is
    for editing in context; this changelist is for searching across BOMs.
    """

    list_display = (
        "bom",
        "raw_material",
        "quantity",
        "unit_of_measure",
        "cost_basis_quantity",
        "cost_reference",
        "organization",
    )
    list_filter = ("unit_of_measure",)
    search_fields = (
        "bom__version",
        "bom__finished_product__name",
        "raw_material__name",
        "raw_material__sku",
        "organization__name",
    )
    list_select_related = (
        "organization",
        "bom",
        "bom__finished_product",
        "raw_material",
    )
    raw_id_fields = ("organization", "bom", "raw_material")
    readonly_fields = ("created_at", "updated_at")
    ordering = (
        "organization__name",
        "bom__finished_product__name",
        "raw_material__name",
    )


# ===========================================================================
# Catalog: Pricing
# ===========================================================================


@admin.register(PricingRule, site=console_site)
class PricingRuleAdmin(TenantScopedAdmin):
    list_display = (
        "rule_type",
        "target_line_type",
        "target_label",
        "priority",
        "is_active",
        "organization",
    )
    list_filter = ("rule_type", "target_line_type", "is_active")
    search_fields = (
        "target_service__name",
        "target_service__code",
        "target_product__name",
        "target_product__sku",
        "organization__name",
    )
    # IMPORTANT: include "organization" explicitly. TenantScopedAdmin sets
    # list_select_related = ("organization",) on the parent, and subclassing
    # replaces rather than extends.
    list_select_related = ("organization", "target_service", "target_product")
    raw_id_fields = ("organization", "target_service", "target_product")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("organization__name", "target_line_type", "-priority")

    @admin.display(description="Target")
    def target_label(self, obj: PricingRule) -> str:
        """Polymorphic target label for the changelist.

        Renders one of:
          - "Service: <name>"  if target_service is set
          - "Product: <name>"  if target_product is set
          - "(default)"        if neither is set (line-type-default rule)
        """
        if obj.target_service_id is not None:
            return f"Service: {obj.target_service.name}"
        if obj.target_product_id is not None:
            return f"Product: {obj.target_product.name}"
        return "(default)"


@admin.register(PricingSnapshot, site=console_site)
class PricingSnapshotAdmin(TenantScopedAdmin):
    """Read-only admin for pricing snapshots.

    Spec §13.3: "PricingSnapshot records are written once and never
    updated." Add/change/delete are forbidden at the admin layer to
    prevent accidental edits to historical pricing records. The
    `is_active` flag flip on supersession happens at the service layer
    (M3 step 4b), not via the admin.

    Read-only enforcement uses the same pattern as M2's AuditEventAdmin —
    overriding has_*_permission() returns False unconditionally.
    """

    list_display = (
        "quote_line_id",
        "line_type",
        "unit_price_final",
        "is_active",
        "engine_version",
        "organization",
        "created_at",
    )
    list_filter = ("line_type", "is_active", "engine_version", "override_applied")
    search_fields = (
        "quote_line_id",
        "organization__name",
    )
    list_select_related = ("organization",)
    readonly_fields = (
        "organization",
        "quote_line_id",
        "line_type",
        "base_cost",
        "markup_amount",
        "discount_amount",
        "unit_price_final",
        "override_applied",
        "override_unit_price",
        "override_reason",
        "inputs",
        "breakdown",
        "is_active",
        "engine_version",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request) -> bool:
        # Snapshots are written by the pricing engine, not by humans.
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        # Snapshots are immutable per spec §13.3.
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        # Snapshots are retained forever — superseded ones flip is_active=False
        # but are never deleted.
        return False
