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
