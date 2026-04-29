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
