"""
Permission evaluator.

Implements the spec §10.2 algorithm:

  1. If user.is_superuser → grant (short-circuit)
  2. If active impersonation session → evaluate as impersonated membership
     (impersonation context is resolved by the caller; this module receives
      the *acting* membership directly)
  3. Retrieve the user's active Membership for the current organization;
     if none → deny
  4. Collect all capabilities from the membership's Roles via RoleCapability
  5. Apply MembershipCapabilityGrant overrides:
       GRANT → adds capability
       DENY  → removes capability (precedence over role grants)
  6. If required capability ∈ final set → grant; else → deny
  7. Object-level: target.organization == acting_org AND status checks pass
  8. Object-level: target falls within Region/Market/Location scope

Steps 7 and 8 live in `object_check()` since not every check is object-scoped.
Step 8's scope evaluation is a stub today — it always returns True. Real
scope enforcement lands in M2 step 4 alongside the operating-scope models.

Caller contract:
  - `has_capability()` is the canonical question. Pass the *acting*
    membership (i.e. the membership whose permissions we're evaluating —
    in non-impersonation cases, the user's own membership).
  - The membership and its organization are an authority pair; the
    evaluator never re-derives one from the other beyond what's needed
    for the active-status check.
  - For per-request batching, pass a request and the evaluator memoizes.

Performance:
  - Without a request cache, two queries per check: one for role
    capabilities, one for grants. select_related is used aggressively
    so the round-trip count stays low.
  - With a request cache, one query per (membership, capability) pair
    over the lifetime of a request.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.platform.organizations.models import Membership
from apps.platform.rbac.models import (
    MembershipCapabilityGrant,
    RoleCapability,
)

# Per-request cache key. We attach a dict to the request object directly
# (not a thread-local) so cleanup is automatic at request end.
_REQUEST_CACHE_ATTR = "_rbac_capability_cache"


def has_capability(
    *,
    user: Any,
    membership: Membership | None,
    capability_code: str,
    request: HttpRequest | None = None,
) -> bool:
    """Decide whether `user` (acting via `membership`) holds `capability_code`.

    Args:
        user: The acting user. For superuser short-circuit. In impersonation,
            this is the SUPPORT user; the membership is the IMPERSONATED
            membership. The caller resolves that distinction before
            calling.
        membership: The acting membership. May be None if no membership
            exists in the current organization, in which case the answer
            is always deny (unless user.is_superuser).
        capability_code: A capability code, e.g. "quotes.approve". Must
            exist in the registry; the evaluator does NOT validate that
            (validation is for tests / CI).
        request: Optional. If provided, results are memoized on the request
            for reuse across multiple checks within a single request.

    Returns:
        True if granted, False if denied. Never raises.
    """
    # ---- Step 1: superuser short-circuit ------------------------------------
    # Per spec §10.2, no further evaluation is performed for superusers.
    # The audit log must still record their actions; that's the audit
    # layer's responsibility, not the evaluator's.
    if user is not None and getattr(user, "is_superuser", False):
        return True

    # ---- Step 2: impersonation handled by caller ----------------------------
    # The caller has already substituted the impersonated membership (if
    # applicable) before calling us. From here on, `membership` IS the
    # acting membership, regardless of impersonation state.

    # ---- Step 3: must have a membership -------------------------------------
    if membership is None:
        return False

    # The membership must be ACTIVE — suspended/inactive memberships
    # cannot exercise capabilities.
    if membership.status != Membership.Status.ACTIVE:
        return False

    # ---- Per-request cache lookup -------------------------------------------
    cache_key = (membership.pk, capability_code)
    if request is not None:
        cache = getattr(request, _REQUEST_CACHE_ATTR, None)
        if cache is None:
            cache = {}
            setattr(request, _REQUEST_CACHE_ATTR, cache)
        if cache_key in cache:
            return cache[cache_key]

    # ---- Steps 4 & 5: compute the effective capability set ------------------
    granted = _compute_effective_capabilities(membership)
    result = capability_code in granted

    # Save to cache for the rest of this request.
    if request is not None:
        cache[cache_key] = result

    return result


def _compute_effective_capabilities(membership: Membership) -> frozenset[str]:
    """Compute the set of capability codes effective for `membership`.

    Steps 4 + 5 of spec §10.2:
      - Union of all RoleCapability codes from the membership's roles
        (via the MembershipRole through table)
      - Plus all GRANT overrides
      - Minus all DENY overrides (DENY wins)

    Returns a frozenset to discourage accidental mutation by callers.

    Two queries: one for role-derived caps (joining MembershipRole →
    Role → RoleCapability → Capability), one for direct grants. Each
    returns just the code strings — no model instantiation. Per-request
    caching by has_capability() amortizes this across multiple checks.
    """
    # Step 4: capabilities granted via assigned roles.
    # Join chain: MembershipRole(membership) → Role → RoleCapability → Capability
    # We pivot from RoleCapability so the queryset is a flat code list.
    role_caps: set[str] = set(
        RoleCapability.objects.filter(
            role__membership_assignments__membership=membership
        ).values_list("capability__code", flat=True)
    )

    # Step 5: GRANT/DENY overrides on the membership directly.
    grants = MembershipCapabilityGrant.objects.filter(
        membership=membership
    ).values_list("capability__code", "grant_type")

    grant_codes = {
        code for code, gt in grants if gt == MembershipCapabilityGrant.GrantType.GRANT
    }
    deny_codes = {
        code for code, gt in grants if gt == MembershipCapabilityGrant.GrantType.DENY
    }

    # (roles ∪ grants) − denies. DENY precedence is the last set operation.
    effective = (role_caps | grant_codes) - deny_codes
    return frozenset(effective)


# ---------------------------------------------------------------------------
# Object-level checks (steps 7 & 8)
# ---------------------------------------------------------------------------


def object_check(
    *,
    user: Any,
    membership: Membership | None,
    capability_code: str,
    target: Any,
    request: HttpRequest | None = None,
) -> bool:
    """Capability check + object-level guards.

    Runs the full §10.2 algorithm including steps 7 and 8:
      - Capability gate (steps 1-6)
      - Target's organization matches the acting membership's organization
      - Target falls within the membership's operating scope (step 8)

    Status checks (e.g., "DRAFT only") are NOT enforced here — those are
    capability-specific and live in service-layer code that knows the
    semantics. The evaluator handles tenancy and scope; service layers
    handle business state.

    Args:
        target: An object with an `organization` attribute (typically a
            FK to Organization). If target lacks `organization`, the
            tenancy check is skipped — appropriate only for objects that
            are inherently global (rare).
    """
    # Step 1: superuser short-circuit ALSO bypasses object-level checks.
    # Spec is explicit on step 1 being the only short-circuit; superuser
    # passes both capability and object steps.
    if user is not None and getattr(user, "is_superuser", False):
        return True

    # Steps 1-6: capability gate.
    if not has_capability(
        user=user,
        membership=membership,
        capability_code=capability_code,
        request=request,
    ):
        return False

    # At this point membership is non-None and ACTIVE (has_capability
    # would have returned False otherwise).
    assert membership is not None  # for type-checker; unreachable on None

    # Step 7: tenancy check. Target's organization must match the acting
    # membership's organization. This is the most-violated rule in
    # multi-tenant apps; enforce it at the evaluator regardless of whether
    # the caller already filtered by org.
    target_org_id = getattr(target, "organization_id", None)
    if target_org_id is not None and target_org_id != membership.organization_id:
        return False

    # Step 8: operating-scope check. Stub until M2 step 4 ships
    # MembershipScopeAssignment + Region/Market/Location models. Returns
    # True today so capability+tenancy checks pass; once scope lands,
    # this delegates to the scope evaluator.
    if not _within_operating_scope(membership=membership, target=target):
        return False

    return True


# Set of system_key values that REQUIRE a matching scope assignment.
# Per spec line 735: a scoped role without a scope assignment grants no
# data access. Keep this in sync with the Role.SystemKey enum members
# that represent geographically-scoped manager roles.
_SCOPED_ROLE_KEYS = frozenset(
    {
        "REGIONAL_MANAGER",
        "MARKET_MANAGER",
        "LOCATION_MANAGER",
    }
)


def _within_operating_scope(*, membership: Membership, target: Any) -> bool:
    """Whether `target` falls within `membership`'s operating-scope assignments.

    Implements spec §7.2A and the §10.2 step 8 algorithm:

      1. Resolve target's scope-location via `target.get_scope_location()`.
         If the target has no such method or returns None, the target is
         org-wide (e.g., a Role, a Catalog item) — step 8 doesn't apply.
      2. If membership has any assigned role with a scoped system_key
         (Regional/Market/Location Manager) but NO scope assignments at
         all, deny — fail-closed safety net per spec line 735. Service
         layer should prevent this state, but the evaluator catches it
         too in case a state slips through.
      3. If membership has no scope assignments AND no scoped roles, it
         has org-wide access — pass.
      4. Otherwise: target's location must fall within at least ONE of
         the membership's scope assignments, with hierarchical widening:
           - LOCATION assignment matches if target.location == assignment.location
           - MARKET assignment matches if target's location is in assignment.market
           - REGION assignment matches if target's location's market is in assignment.region
    """
    # Step 1: resolve the target's scope-location.
    get_scope_loc = getattr(target, "get_scope_location", None)
    if get_scope_loc is None:
        # Target is not scope-aware → treat as org-wide. Skip step 8.
        return True
    target_location = get_scope_loc()
    if target_location is None:
        # Target is org-wide (Catalog, Role, etc.). Skip step 8.
        return True

    # Step 2 & 3: determine the membership's scope posture.
    assignments = list(
        membership.scope_assignments.select_related("region", "market", "location")
    )
    has_scoped_role = _membership_has_scoped_role(membership)

    if not assignments:
        if has_scoped_role:
            # Defense-in-depth: scoped role with no scope assignment
            # cannot access any data targets.
            return False
        # Unscoped membership (e.g., Owner, Sales Staff) — org-wide access.
        return True

    # Step 4: target location must match at least one assignment.
    # We widen by walking up the target's hierarchy ONCE rather than
    # querying per-assignment, so the cost is O(assignments) not O(N×M).
    target_market = target_location.market
    target_region_id = target_market.region_id

    for assignment in assignments:
        if assignment.location_id is not None:
            if assignment.location_id == target_location.pk:
                return True
        elif assignment.market_id is not None:
            if assignment.market_id == target_market.pk:
                return True
        elif assignment.region_id is not None:
            if assignment.region_id == target_region_id:
                return True

    # No assignment matched.
    return False


def _membership_has_scoped_role(membership: Membership) -> bool:
    """Whether the membership holds any role that requires a scope assignment.

    Used by the fail-closed defense in _within_operating_scope. Avoids a
    join through RoleCapability; we just look at the role's system_key.
    """
    # MembershipRole is in the rbac app; importing here keeps the evaluator
    # free of model-import-cycle worries at module load.
    from apps.platform.rbac.models import MembershipRole

    return MembershipRole.objects.filter(
        membership=membership,
        role__system_key__in=_SCOPED_ROLE_KEYS,
    ).exists()


# ---------------------------------------------------------------------------
# Helpers for callers
# ---------------------------------------------------------------------------


def get_acting_membership(*, user: Any, organization: Any) -> Membership | None:
    """Resolve the membership a user is acting through in `organization`.

    Future impersonation support: this is where impersonation context
    gets resolved. When impersonation lands, this helper checks the
    request's impersonation session and returns the impersonated
    membership instead of the user's own.

    Today: returns the user's own ACTIVE membership in `organization`,
    or None if no such membership exists.

    Returns None for unauthenticated users so callers don't need to
    branch on `user.is_authenticated` themselves.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    if organization is None:
        return None

    return Membership.objects.filter(
        user=user,
        organization=organization,
        status=Membership.Status.ACTIVE,
    ).first()
