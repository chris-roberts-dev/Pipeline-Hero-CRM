"""
System role templates.

Declarative mapping of each system-defined default role (spec §10.4) to the
set of capabilities it's seeded with. Organization creation copies these
templates into per-org Role rows via the service layer.

Edit discipline:
  - ADDING a new template: append a SystemRoleTemplate. A new default role
    gets seeded to EXISTING organizations by running the role-sync service
    (not implemented in v1; re-seed is a manual operation via a management
    command if needed).
  - CHANGING an existing template's capability set: update the module here,
    but remember that existing organizations WON'T automatically get the
    new capabilities. Role seeding is run-once-at-org-creation. Changing
    the template affects new orgs only. If a retroactive update is
    required, write a one-off data migration that explicitly targets
    existing organizations.
  - REMOVING or RENAMING a SystemKey is forbidden — memberships reference
    roles by pk, but system_key identity is how we look up "the Owner role
    for org X" from services. A rename would orphan every lookup.

Manager roles (Regional, Market, Location):
  Spec §10.4 says Manager roles are "all except platform-level actions;
  restricted to their assigned Region/Market/Location scope." V1 has no
  platform-level capabilities in the §10.3 registry — every capability is
  tenant-scoped — so Manager roles functionally get ALL capabilities at
  the capability level. Scope enforcement (which narrows the data these
  roles can ACCESS) is a separate mechanism landing in M2 step 4.

Owner vs Org Admin:
  Both currently get ALL capabilities. The spec distinguishes them
  ("Owner: all; Org Admin: all except platform-level"), but v1 has no
  platform-level capabilities so the distinction is dormant. Preserved as
  separate role templates so the distinction can become meaningful later
  without a schema change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.platform.rbac.capabilities import CAPABILITIES, all_codes
from apps.platform.rbac.models import Role


# Sentinel used instead of spelling out every capability code for broad
# roles (Owner, Org Admin, Managers). Resolved at seeding time to the full
# registry. Using a singleton instance rather than a class keeps equality
# checks cheap and unambiguous.
class _AllCapabilitiesMarker:
    __slots__ = ()

    def __repr__(self) -> str:
        return "ALL_CAPABILITIES"


ALL_CAPABILITIES = _AllCapabilitiesMarker()


@dataclass(frozen=True)
class SystemRoleTemplate:
    """A default-role definition: the role itself plus its capability set.

    `capabilities` is either:
      - the ALL_CAPABILITIES sentinel, meaning "every capability in the
        registry at seed time", OR
      - a set of capability code strings, OR
      - the special string "*.view" which means "every code ending in .view"
    """

    system_key: str
    name: str
    description: str
    capabilities: object  # ALL_CAPABILITIES | set[str] | str
    sort_order: int = 0  # Lower = higher in the UI. Ownership-level roles first.


# ---------------------------------------------------------------------------
# Sales Staff — spec §10.4 narrow capability list
# ---------------------------------------------------------------------------
# The spec lists: leads.*, quotes.view/create/edit/send, clients.view/create/edit,
# tasks.view/create/edit, communications.view/log, orders.view, catalog.view.
_SALES_STAFF_CAPS = {
    # Every leads.* capability
    "leads.view", "leads.create", "leads.edit", "leads.edit_any",
    "leads.archive", "leads.convert", "leads.assign",
    # Selective quotes
    "quotes.view", "quotes.create", "quotes.edit", "quotes.send",
    # Selective clients
    "clients.view", "clients.create", "clients.edit",
    # Selective tasks
    "tasks.view", "tasks.create", "tasks.edit",
    # Communications (log only, not send — salespeople log manual
    # interactions; outbound send is a separate action)
    "communications.view", "communications.log",
    # Read-only orders + catalog
    "orders.view",
    "catalog.view",
}


# ---------------------------------------------------------------------------
# Service Staff — spec §10.4: work orders + tasks, own-only unless elevated
# ---------------------------------------------------------------------------
_SERVICE_STAFF_CAPS = {
    "workorders.view",
    "workorders.update_status",
    "workorders.complete",
    "tasks.view",
    "tasks.complete",
}


# ---------------------------------------------------------------------------
# Production Staff — spec §10.4: build + labor + tasks
# ---------------------------------------------------------------------------
_PRODUCTION_STAFF_CAPS = {
    "build.view",
    "build.manage",
    "build.labor.record",
    "tasks.view",
    "tasks.complete",
}


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------
# Sort order sets the default display ranking in the admin and org-admin
# role-management UI: owner/admin first, scope managers next, staff roles,
# viewer last.

SYSTEM_ROLE_TEMPLATES: list[SystemRoleTemplate] = [
    SystemRoleTemplate(
        system_key=Role.SystemKey.OWNER,
        name="Owner",
        description="Full administrative access to the organization.",
        capabilities=ALL_CAPABILITIES,
        sort_order=10,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.ORG_ADMIN,
        name="Org Admin",
        description=(
            "All organization-level capabilities. Distinct from Owner only "
            "when platform-level capabilities are added in a future release."
        ),
        capabilities=ALL_CAPABILITIES,
        sort_order=20,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.REGIONAL_MANAGER,
        name="Regional Manager",
        description=(
            "All capabilities within the assigned Region scope. Requires a "
            "Region operating-scope assignment on the membership."
        ),
        capabilities=ALL_CAPABILITIES,
        sort_order=30,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.MARKET_MANAGER,
        name="Market Manager",
        description=(
            "All capabilities within the assigned Market scope. Requires a "
            "Market operating-scope assignment on the membership."
        ),
        capabilities=ALL_CAPABILITIES,
        sort_order=40,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.LOCATION_MANAGER,
        name="Location Manager",
        description=(
            "All capabilities within the assigned Location scope. Requires a "
            "Location operating-scope assignment on the membership."
        ),
        capabilities=ALL_CAPABILITIES,
        sort_order=50,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.SALES_STAFF,
        name="Sales Staff",
        description="Lead and quote management, client and task creation, communication logging.",
        capabilities=_SALES_STAFF_CAPS,
        sort_order=60,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.SERVICE_STAFF,
        name="Service Staff",
        description="Field service work orders and task completion for own assignments.",
        capabilities=_SERVICE_STAFF_CAPS,
        sort_order=70,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.PRODUCTION_STAFF,
        name="Production Staff",
        description="Shop-floor build orders, labor entry, and task completion.",
        capabilities=_PRODUCTION_STAFF_CAPS,
        sort_order=80,
    ),
    SystemRoleTemplate(
        system_key=Role.SystemKey.VIEWER,
        name="Viewer",
        description="Read-only access across all domains — no mutations.",
        capabilities="*.view",  # resolved to every code ending in .view
        sort_order=90,
    ),
]


def resolve_capability_codes(template: SystemRoleTemplate) -> set[str]:
    """Expand a template's capability spec to a concrete set of codes.

    Called at seed time against the current capability registry. Called
    once per role per org, so performance here is uninteresting; clarity
    is what matters.
    """
    caps = template.capabilities

    if caps is ALL_CAPABILITIES:
        return set(all_codes())

    if caps == "*.view":
        # Every code ending in `.view`. The permission evaluator treats
        # these as read-only capabilities; the Viewer role gets exactly
        # that set and nothing else.
        return {c.code for c in CAPABILITIES if c.code.endswith(".view")}

    if isinstance(caps, set):
        # Validate every code actually exists in the registry. A typo here
        # would silently skip a capability; failing loudly is better.
        unknown = caps - set(all_codes())
        if unknown:
            raise ValueError(
                f"System role template {template.system_key!r} references "
                f"unknown capabilities: {sorted(unknown)}"
            )
        return set(caps)

    raise TypeError(
        f"Unsupported capabilities spec for template {template.system_key!r}: "
        f"{type(caps).__name__}"
    )


# ---------------------------------------------------------------------------
# Import-time self-checks
# ---------------------------------------------------------------------------
# These run once on module import. Cheap and catch registry drift before
# the code ever reaches a running server.

_system_keys = [t.system_key for t in SYSTEM_ROLE_TEMPLATES]
if len(_system_keys) != len(set(_system_keys)):
    dupes = {k for k in _system_keys if _system_keys.count(k) > 1}
    raise RuntimeError(f"Duplicate system_key values in role templates: {sorted(dupes)}")

# Every enum value in Role.SystemKey must have a matching template.
# Catches the case where someone adds an enum value but forgets the template.
_enum_keys = {choice.value for choice in Role.SystemKey}
_template_keys = {t.system_key for t in SYSTEM_ROLE_TEMPLATES}
if _enum_keys != _template_keys:
    missing = _enum_keys - _template_keys
    extra = _template_keys - _enum_keys
    raise RuntimeError(
        f"Role.SystemKey / template mismatch. "
        f"Missing templates: {sorted(missing)}. "
        f"Extra templates: {sorted(extra)}."
    )
