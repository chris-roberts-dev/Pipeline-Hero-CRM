"""
Organization and Membership models.

Organization is the tenant entity. It is NOT itself a TenantModel because it
has no parent organization to scope against — it *is* the tenant. Membership
IS a TenantModel: each membership belongs to exactly one organization.

Spec refs:
  - §7.1  row-based tenancy, every tenant-owned record carries an `organization` FK
  - §8.2  user may belong to multiple organizations via Membership
  - §9.2  subdomain routing uses `slug` — must be unique, subdomain-safe
  - §6.9  Membership state machine (Invited, Active, Suspended, Inactive, Expired)

Design notes:
  - `slug` is the subdomain segment. Validated at the field level to allow
    only lowercase alphanumerics and hyphens, and it must fit inside a DNS
    label (63 chars). We DO NOT pre-emptively reject reserved words like
    "www" or "admin" here — that's tenant-admin-policy territory, better
    handled in the organization creation service than in the model itself.
  - `status` uses a TextChoices enum instead of boolean flags. Spec §25.6
    says Organizations are soft-deactivate-only; the status field gives room
    to distinguish ACTIVE / INACTIVE / SUSPENDED cleanly later without
    another migration.
  - Role assignment on Membership is deferred to M2. The `roles` M2M is
    intentionally omitted from this migration — adding it when we introduce
    Role is cleaner than shipping an empty relation now.
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.tenancy.models import TenantModel

# DNS label constraints: lowercase alphanumerics and hyphens, must not start
# or end with a hyphen, up to 63 chars. We enforce length separately via
# max_length so this regex focuses on the character-class + boundary rules.
_SLUG_VALIDATOR = RegexValidator(
    regex=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$",
    message=_(
        "Slug must be lowercase alphanumerics with optional hyphens, "
        "not starting or ending with a hyphen."
    ),
)


class Organization(models.Model):
    """A tenant organization. The root of every tenant-owned relationship.

    NOT a TenantModel — an Organization does not belong to a parent org.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        SUSPENDED = "SUSPENDED", _("Suspended")

    name = models.CharField(_("name"), max_length=200)

    # Subdomain segment. `{slug}.mypipelinehero.com` resolves the tenant.
    slug = models.SlugField(
        _("slug"),
        max_length=63,
        unique=True,
        validators=[_SLUG_VALIDATOR],
        help_text=_("Used as the tenant subdomain. Lowercase, alphanumerics and hyphens."),
    )

    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ["name"]
        indexes = [
            # Fast slug resolution for TenancyMiddleware. The unique=True on
            # slug already creates an index; this index is explicit for
            # status+slug lookups when we need to resolve "active org by slug".
            models.Index(fields=["status", "slug"], name="org_status_slug_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    @property
    def is_active(self) -> bool:
        """Convenience: distinguishes 'usable tenant' from merely 'existing row'.

        TenancyMiddleware and the handoff-completion view will check this
        before establishing a tenant session. Inactive/suspended orgs must
        fail safely per spec §9.2.
        """
        return self.status == self.Status.ACTIVE


class Membership(TenantModel):
    """A user's membership in an organization.

    A user has one Membership per organization they belong to. Role and
    scope-assignment relations are layered on in M2 (RBAC + Region/Market/Location).
    """

    class Status(models.TextChoices):
        INVITED = "INVITED", _("Invited")
        ACTIVE = "ACTIVE", _("Active")
        SUSPENDED = "SUSPENDED", _("Suspended")
        INACTIVE = "INACTIVE", _("Inactive")
        EXPIRED = "EXPIRED", _("Expired")

    # `organization` FK, created_at, updated_at come from TenantModel.

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="memberships",
    )

    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.INVITED,
        db_index=True,
    )

    # Audit metadata required by spec §8.3.
    invited_at = models.DateTimeField(blank=True, null=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    activated_at = models.DateTimeField(blank=True, null=True)
    deactivated_at = models.DateTimeField(blank=True, null=True)

    # If a user belongs to multiple orgs, the one flagged as default is where
    # they land after login when no specific org context is in play.
    # Enforced as "at most one default per user" via the constraint below.
    is_default = models.BooleanField(
        _("default membership"),
        default=False,
        help_text=_("Post-login landing org for this user when none is selected."),
    )

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        ordering = ["organization__name", "user__email"]
        constraints = [
            # A user has at most one membership per organization.
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="membership_user_org_unique",
            ),
            # At most one default membership per user. Partial index —
            # only enforced on rows where is_default=True, so users without
            # a default simply have zero rows matching the constraint.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="membership_single_default_per_user",
            ),
        ]
        indexes = [
            # Common query: "all active memberships for this user".
            models.Index(fields=["user", "status"], name="membership_user_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.organization.slug} ({self.status})"
