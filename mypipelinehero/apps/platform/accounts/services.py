"""
Authentication service.

Views call these functions. They return plain Python objects (dataclasses or
model instances), not HTTP responses. Views translate the return values or
caught exceptions into templates, redirects, or errors.

Scope in M1:
  - Password authentication against the custom User model
  - Post-auth routing decision: where should this user land?

Out of scope here (explicit):
  - Session management — Django's login() is called by the view, not the
    service. The service returns the authenticated user; the view decides
    what session semantics to apply.
  - Rate limiting — spec §26.2 requires this on login, but it's middleware
    territory, not domain logic. Deferred to M6 hardening.
  - Password reset / invite flows — separate service functions, added when
    those views are built.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.common.services import AuthenticationError
from apps.platform.organizations.models import Membership, Organization

User = get_user_model()


@dataclass(frozen=True)
class LoginResult:
    """What the login view needs to decide where to send the user next.

    `user` is always set on success. The other fields describe the post-auth
    routing decision:

      - `is_platform_user=True` + no memberships: send to platform console
      - `default_org` set: exactly one membership (or one default) — direct to that org
      - `selectable_orgs` non-empty: show org picker
      - none of the above: dead end, render a "no memberships, no platform access" page
    """

    user: "User"
    is_platform_user: bool
    default_org: Optional[Organization]
    selectable_orgs: QuerySet


def login_with_password(*, email: str, password: str) -> LoginResult:
    """Validate credentials and return the routing decision.

    Raises AuthenticationError on any credential failure. Never reveals
    whether an email is registered — the message is the same for "unknown
    email" and "wrong password" to avoid user enumeration.
    """
    # Django's authenticate() respects AUTH_USER_MODEL and runs the model
    # backend's `authenticate()` method, which applies `is_active` filtering.
    # Inactive users are rejected here automatically.
    user = authenticate(username=email, password=password)
    if user is None:
        raise AuthenticationError("Invalid email or password.")

    return _build_login_result(user)


def _build_login_result(user) -> LoginResult:
    """Compute routing based on the user's memberships.

    Ordering of rules matters. We check memberships first even for platform
    users — a super-admin who also happens to be a member of an org should
    still see the org picker; they can reach the platform console from there.
    """
    active_memberships = Membership.objects.filter(
        user=user,
        status=Membership.Status.ACTIVE,
        organization__status=Organization.Status.ACTIVE,
    ).select_related("organization")

    default = None
    selectable = active_memberships

    if active_memberships.count() == 1:
        # Single-org users skip the picker.
        default = active_memberships.first().organization
        selectable = active_memberships.none()
    else:
        # Multi-org users: if one is flagged as default, pre-select it but
        # still show the picker (user may have bookmarked a different org or
        # legitimately want to switch today).
        default_mem = active_memberships.filter(is_default=True).first()
        if default_mem is not None:
            default = default_mem.organization

    return LoginResult(
        user=user,
        is_platform_user=bool(user.is_staff or user.is_superuser),
        default_org=default,
        selectable_orgs=selectable,
    )


def user_can_access_org(*, user, organization: Organization) -> bool:
    """Return True if the user has an ACTIVE membership in the given org.

    Platform super-admins are NOT auto-granted access via this method —
    they get a separate impersonation path (M2). The handoff flow uses
    this function to validate the org selection is one the user can
    actually claim.
    """
    if not organization.is_active:
        return False
    return Membership.objects.filter(
        user=user,
        organization=organization,
        status=Membership.Status.ACTIVE,
    ).exists()
