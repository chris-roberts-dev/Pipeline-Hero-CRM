"""
Tenant-portal services.

The tenant subdomain's counterpart to the root-domain auth portal. When a
handoff token arrives at `/auth/handoff?token=...`, this service validates
the token, ensures the user still has an active membership in the target
org, and returns the user + organization so the view can call Django's
`login()` to establish a tenant-local session.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model

from apps.common.services import AuthenticationError, ValidationError
from apps.platform.accounts.services import user_can_access_org
from apps.platform.organizations.models import Organization
from apps.web.auth_portal.services import redeem as redeem_handoff_token

User = get_user_model()


@dataclass(frozen=True)
class HandoffResult:
    """What the handoff-completion view needs to establish a tenant session."""

    user: "User"
    organization: Organization


def complete_handoff(*, token: str, expected_organization: Organization) -> HandoffResult:
    """Validate a handoff token against the tenant we're on.

    The `expected_organization` is the org resolved by TenancyMiddleware from
    the subdomain — the token's claim MUST match, otherwise someone is
    trying to use a token issued for org A at the subdomain of org B.

    Raises:
        AuthenticationError: token invalid / expired / replayed / tampered.
        ValidationError: token is valid but claims a different org, or the
            user's membership has since been revoked/suspended.
    """
    claim = redeem_handoff_token(token)
    if claim is None:
        raise AuthenticationError("Handoff token is invalid or has expired.")

    if claim.organization_id != expected_organization.pk:
        # Token was issued for a different org than the subdomain we're on.
        # This is a routing error at best; at worst, a deliberate misuse.
        # Either way, refuse the handoff and audit the attempt.
        raise ValidationError("Handoff token does not match this organization.")

    try:
        user = User.objects.get(pk=claim.user_id, is_active=True)
    except User.DoesNotExist as e:
        raise AuthenticationError("User is no longer active.") from e

    # Re-check membership at redemption time. The token was issued seconds
    # ago, but a lot can happen in 60s — an admin could have deactivated
    # the membership. The check at issue time is not sufficient.
    if not user_can_access_org(user=user, organization=expected_organization):
        raise ValidationError("Membership is no longer active in this organization.")

    return HandoffResult(user=user, organization=expected_organization)
