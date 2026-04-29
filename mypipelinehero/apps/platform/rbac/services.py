"""
RBAC service layer.

Today: role seeding at organization creation time. Future additions (role
assignment, grant/revoke, capability override management) will live here.

Design:
  - `seed_default_roles_for_org(org)` idempotently creates the 9 system
    roles for an organization and attaches the correct capability set to
    each, per the templates in `role_templates.py`.
  - Fully idempotent. Running twice against the same org re-syncs the
    roles' capability sets against the current template definitions.
    Running against an org that already has the roles is a no-op.
  - Summary-level return value — the organization creation service uses
    it to emit a single audit event rather than one event per role.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.platform.organizations.models import Organization
from apps.platform.rbac.capabilities import all_codes
from apps.platform.rbac.models import Capability, Role, RoleCapability
from apps.platform.rbac.role_templates import (
    SYSTEM_ROLE_TEMPLATES,
    resolve_capability_codes,
)


@dataclass(frozen=True)
class RoleSeedResult:
    """Summary of a seeding run, used for audit and caller introspection."""

    roles_created: int
    roles_updated: int
    capability_links_created: int
    capability_links_removed: int


@transaction.atomic
def seed_default_roles_for_org(organization: Organization) -> RoleSeedResult:
    """Create (or re-sync) the 9 system default roles for an organization.

    Idempotent by design:
      - If a role with a given `system_key` already exists for the org,
        it is left in place and its capability assignments are re-synced
        against the current template (NOT the org's current assignments
        — templates are authoritative for system roles).
      - If a role does not exist, it is created.
      - Capability links that the template now defines but aren't yet
        present are added. Capability links that exist but are NOT in the
        current template are removed, to prevent drift between what the
        platform ships and what a given org has.
      - Only system roles (is_system=True) are touched. Tenant-custom
        roles are completely ignored.

    This function MUST remain safe to call repeatedly. The organization
    creation flow runs it once; a future management command may run it
    again to bring an existing tenant up to date with a new platform
    release's template set.
    """
    # Prefetch the full capability table once — cheap (84 rows) and avoids
    # 9-role × N-cap round-trips to the DB.
    code_to_capability: dict[str, Capability] = {
        cap.code: cap for cap in Capability.objects.all()
    }

    # Safety check: the registry-vs-DB sync is the data migration's job;
    # we're downstream of that. But if somebody's deleted rows out from
    # under us, fail loudly rather than silently skipping capabilities.
    registry_codes = set(all_codes())
    db_codes = set(code_to_capability.keys())
    missing_from_db = registry_codes - db_codes
    if missing_from_db:
        raise RuntimeError(
            "Capability registry is out of sync with the database. Run the "
            f"0002_seed_capabilities migration. Missing: {sorted(missing_from_db)}"
        )

    roles_created = 0
    roles_updated = 0
    links_created = 0
    links_removed = 0

    for template in SYSTEM_ROLE_TEMPLATES:
        target_codes = resolve_capability_codes(template)

        role, created = Role.objects.update_or_create(
            organization=organization,
            system_key=template.system_key,
            defaults={
                "name": template.name,
                "description": template.description,
                "is_system": True,
            },
        )
        if created:
            roles_created += 1
        else:
            roles_updated += 1

        # Current capability links for this role. Single query.
        existing_links = {
            rc.capability.code: rc
            for rc in RoleCapability.objects.select_related("capability").filter(
                role=role
            )
        }

        existing_codes = set(existing_links.keys())

        # Add links the template defines but aren't in the DB yet.
        to_add = target_codes - existing_codes
        new_links = [
            RoleCapability(
                organization=organization,
                role=role,
                capability=code_to_capability[code],
            )
            for code in to_add
        ]
        if new_links:
            RoleCapability.objects.bulk_create(new_links)
            links_created += len(new_links)

        # Remove links the DB has but the template no longer defines.
        # Prevents stale capabilities from lingering if a template is
        # tightened in a later release. Tenant-custom grants live on
        # MembershipCapabilityGrant, NOT on system-role capability links —
        # so removing these is safe and intentional.
        to_remove = existing_codes - target_codes
        if to_remove:
            deleted, _ = RoleCapability.objects.filter(
                role=role, capability__code__in=to_remove
            ).delete()
            links_removed += deleted

    return RoleSeedResult(
        roles_created=roles_created,
        roles_updated=roles_updated,
        capability_links_created=links_created,
        capability_links_removed=links_removed,
    )


# ---------------------------------------------------------------------------
# Role assignment / scope assignment services
# ---------------------------------------------------------------------------
# Per spec §7.2A line 735: scoped Manager roles require a matching scope
# assignment. Enforced at the service layer to prevent inconsistent state.

# Mirrored from evaluator._SCOPED_ROLE_KEYS — keep in sync. We don't import
# from evaluator here because the dependency direction is services → models,
# and the evaluator imports services (transitively). Duplicating the small
# constant avoids the cycle.
_SCOPED_ROLE_KEYS = frozenset(
    {
        "REGIONAL_MANAGER",
        "MARKET_MANAGER",
        "LOCATION_MANAGER",
    }
)


@transaction.atomic
def assign_role_to_membership(*, membership, role) -> MembershipRole:
    """Assign `role` to `membership`, enforcing the scope invariant.

    Raises:
        ValidationError: if `role` is a scoped Manager role and the
            membership has no scope assignments.
        ValidationError: if role and membership are in different
            organizations (defense against cross-tenant assignment).

    Idempotent: re-assigning an already-assigned role is a no-op (returns
    the existing assignment row).
    """
    from apps.common.services import ValidationError
    from apps.platform.rbac.models import MembershipRole

    # Tenant safety: roles and memberships must be in the same org.
    if role.organization_id != membership.organization_id:
        raise ValidationError("Cannot assign a role from a different organization.")

    # Spec §7.2A line 735: scoped roles require a scope assignment.
    if role.system_key in _SCOPED_ROLE_KEYS:
        if not membership.scope_assignments.exists():
            raise ValidationError(
                f"Role '{role.name}' requires at least one operating-scope "
                f"assignment on the membership before it can be assigned."
            )

    assignment, _ = MembershipRole.objects.get_or_create(
        organization=membership.organization,
        membership=membership,
        role=role,
    )
    return assignment


@transaction.atomic
def remove_role_from_membership(*, membership, role) -> bool:
    """Remove a role assignment. Returns True if a row was deleted."""
    from apps.platform.rbac.models import MembershipRole

    deleted, _ = MembershipRole.objects.filter(
        membership=membership, role=role
    ).delete()
    return deleted > 0


@transaction.atomic
def add_scope_assignment(
    *,
    membership,
    region=None,
    market=None,
    location=None,
    reason: str = "",
) -> MembershipScopeAssignment:
    """Add a scope assignment to a membership.

    Exactly one of `region`, `market`, or `location` must be provided.
    The DB CHECK constraint enforces this too, but raising here gives a
    clearer error than an IntegrityError.

    Raises:
        ValidationError: if zero or more-than-one targets provided, or
            target's organization differs from membership's.
    """
    from apps.common.services import ValidationError
    from apps.platform.rbac.models import MembershipScopeAssignment

    targets = [t for t in (region, market, location) if t is not None]
    if len(targets) != 1:
        raise ValidationError(
            "Exactly one of region, market, or location must be provided."
        )

    target = targets[0]
    if target.organization_id != membership.organization_id:
        raise ValidationError(
            "Scope target must belong to the same organization as the membership."
        )

    return MembershipScopeAssignment.objects.create(
        organization=membership.organization,
        membership=membership,
        region=region,
        market=market,
        location=location,
        reason=reason,
    )


@transaction.atomic
def remove_scope_assignment(*, assignment) -> None:
    """Remove a scope assignment, blocking removal if it would orphan
    a scoped role on the membership.

    Spec §7.2A line 735 implication: a Manager role without scope
    assignments grants no data access. We could allow the orphan and
    let the evaluator's defense-in-depth cover it, but the better UX
    is to surface the inconsistency at the time of attempted removal.

    Raises:
        ValidationError: if removing this assignment would leave the
            membership with a scoped role and no other scope assignments.
    """
    from apps.common.services import ValidationError
    from apps.platform.rbac.models import MembershipRole

    membership = assignment.membership

    # If this isn't the last scope assignment, removal is always fine.
    if membership.scope_assignments.exclude(pk=assignment.pk).exists():
        assignment.delete()
        return

    # Last scope assignment. Check for scoped roles.
    has_scoped_role = MembershipRole.objects.filter(
        membership=membership,
        role__system_key__in=_SCOPED_ROLE_KEYS,
    ).exists()

    if has_scoped_role:
        raise ValidationError(
            "Cannot remove the last scope assignment while a scoped "
            "Manager role is still assigned. Remove the role first, or "
            "add another scope assignment before removing this one."
        )

    assignment.delete()
