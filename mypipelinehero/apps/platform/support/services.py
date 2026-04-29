"""
Impersonation services.

The two operations that have substance:
  - `start_impersonation(...)` — create a new session, with capability,
    target-validity, and reason checks
  - `end_impersonation(...)` — close an active session

Plus a small read-side helper:
  - `get_active_session(session_id)` — middleware lookup, also handles
    lazy expiry detection

Design decisions worth noting:

1. The capability check uses the existing evaluator. Even though a future
   platform-staff role would hold this capability without superuser status,
   today only superusers can pass step 1 of the evaluator. That's
   intentional — v1 doesn't have a non-superuser support flow. The
   evaluator path is identical for both cases, so when platform-staff
   roles ship, no service-layer changes are needed here.

2. We do NOT issue a handoff token from this layer. The view layer (when
   it lands) will call `start_impersonation()` and then issue a handoff
   token using the existing M1 token machinery. Service layer stays
   focused on the data-modeling concern — the cookie-flip-and-redirect
   dance is a view concern.

3. Self-end is always allowed. Force-ending another support user's
   session requires `support.impersonation.end_any`. Spec §7.4 line 439
   says sessions are reversible; whose-reversibility isn't specified, but
   restricting force-end to a separate capability follows the principle
   of least privilege.

4. Reason length: minimum 10 chars. Spec line 436 mandates a reason but
   doesn't specify length. 10 chars catches "x" and "test" without being
   user-hostile. Validation lives here at the service layer, not on the
   model field, so test fixtures can still write tighter rows if needed.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.services import (
    PermissionDeniedError,
    ValidationError,
)
from apps.platform.audit.services import emit as audit_emit
from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.evaluator import has_capability
from apps.platform.support.models import ImpersonationSession

_REASON_MIN_LENGTH = 10
_END_ANY_CAPABILITY = "support.impersonation.end_any"
_START_CAPABILITY = "support.impersonation.start"


@transaction.atomic
def start_impersonation(
    *,
    support_user: Any,
    target_user: Any,
    target_organization: Organization,
    reason: str,
    request: Any | None = None,
) -> ImpersonationSession:
    """Begin an impersonation session.

    Args:
        support_user: The user invoking the impersonation. Must hold
            `support.impersonation.start` (or be a superuser).
        target_user: The user being impersonated.
        target_organization: The org context for the session.
        reason: Mandatory free-text rationale (spec §7.4 line 436). Empty
            or trivially short reasons are rejected.
        request: Optional. Used for audit metadata (IP, user-agent) and
            to derive on_behalf_of. Not stored on the session itself.

    Returns:
        The persisted ImpersonationSession.

    Raises:
        PermissionDeniedError: support_user lacks the start capability.
        ValidationError: reason too short, target user has no active
            membership in the org, or other invariant violations.
    """
    # Capability gate. The evaluator's superuser short-circuit means
    # superusers always pass here; non-superusers need the explicit cap.
    # We pass membership=None because impersonation is platform-level —
    # the support user has no tenant membership of their own.
    if not has_capability(
        user=support_user,
        membership=None,
        capability_code=_START_CAPABILITY,
    ):
        raise PermissionDeniedError(
            "Impersonation requires the support.impersonation.start capability."
        )

    # Reason validation.
    reason = (reason or "").strip()
    if len(reason) < _REASON_MIN_LENGTH:
        raise ValidationError(
            f"A meaningful reason of at least {_REASON_MIN_LENGTH} "
            f"characters is required."
        )

    # Identity sanity checks. These are cheap and obvious — running them
    # before the DB lookup means error messages are accurate even when
    # multiple invariants are violated at once (e.g. self-impersonating
    # with no membership: report self-impersonation, not missing-membership).
    if target_user == support_user:
        raise ValidationError("Cannot impersonate yourself.")
    if getattr(target_user, "is_superuser", False):
        # Defense-in-depth: allowing impersonation of a superuser by a
        # support user would let the support user escalate via the
        # impersonated session.
        raise ValidationError("Cannot impersonate a superuser.")

    # Resolve the target's active membership. Spec §10.2 step 2: capability
    # checks during impersonation evaluate against the impersonated
    # MEMBERSHIP — so the target must actually have one in this org.
    try:
        target_membership = Membership.objects.get(
            user=target_user,
            organization=target_organization,
            status=Membership.Status.ACTIVE,
        )
    except Membership.DoesNotExist as exc:
        raise ValidationError(
            f"User {target_user} has no active membership in " f"{target_organization}."
        ) from exc

    # (self/superuser identity checks moved above so error messages are
    # accurate when multiple invariants are violated.)

    # Compute expiry. Settings-driven so production can dial it.
    ttl_minutes = getattr(settings, "IMPERSONATION_TTL_MINUTES", 30)
    ends_at = timezone.now() + timedelta(minutes=ttl_minutes)

    # Capture forensic metadata at start time. The middleware doesn't
    # need any of this; it's purely for after-the-fact investigation.
    metadata = {
        "ttl_minutes": ttl_minutes,
    }
    if request is not None:
        metadata["ip_address"] = _safe_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "") if hasattr(request, "META") else ""
        if ua:
            metadata["user_agent"] = ua[:256]

    session = ImpersonationSession.objects.create(
        support_user=support_user,
        target_user=target_user,
        target_organization=target_organization,
        target_membership=target_membership,
        reason=reason,
        ends_at=ends_at,
        metadata=metadata,
    )

    # Session-level audit (spec §22.1 line 1561 and §27 line 1850).
    # Note: actor IS the support user; on_behalf_of is None for the
    # session-start event itself because at start time, no impersonation
    # is "active yet" from the audit's point of view.
    audit_emit(
        event_type="IMPERSONATION_STARTED",
        actor_user=support_user,
        organization=target_organization,
        target=("support.ImpersonationSession", session.pk),
        metadata={
            "session_id": session.session_id,
            "target_user_id": target_user.pk,
            "ends_at": ends_at.isoformat(),
            "reason": reason,
        },
        request=request,
    )

    return session


@transaction.atomic
def end_impersonation(
    *,
    session: ImpersonationSession,
    ending_user: Any,
    end_reason: str = "",
    request: Any | None = None,
) -> ImpersonationSession:
    """End an impersonation session.

    Args:
        session: The session to end.
        ending_user: Who is ending it. Self-end (ending_user == support_user)
            is always allowed. Force-end requires support.impersonation.end_any.
        end_reason: Free-form note. Optional but recommended for force-end.

    Raises:
        ValidationError: session is already ended.
        PermissionDeniedError: force-end attempted without the end_any cap.

    Returns:
        The same session, updated with ended_at and end_reason.
    """
    # Already-ended sessions can't be re-ended. Treat this as a service
    # error rather than silently ignoring — caller should know.
    if session.ended_at is not None:
        raise ValidationError("Session is already ended.")

    is_self_end = ending_user is not None and ending_user.pk == session.support_user_id
    if not is_self_end:
        # Force-end check.
        if not has_capability(
            user=ending_user,
            membership=None,
            capability_code=_END_ANY_CAPABILITY,
        ):
            raise PermissionDeniedError(
                "Ending another user's impersonation session requires the "
                "support.impersonation.end_any capability."
            )

    session.ended_at = timezone.now()
    session.ended_by = ending_user
    session.end_reason = end_reason or ("self_end" if is_self_end else "force_end")
    session.save(update_fields=["ended_at", "ended_by", "end_reason"])

    # Session-level audit. Per spec §10.2 step 2 and §22.1 line 1561,
    # the END event still records the support user as actor — and on the
    # END action specifically, on_behalf_of is None because by the time we
    # emit, the session is no longer "active." The middleware would set
    # on_behalf_of for in-session actions; END is post-session.
    audit_emit(
        event_type="IMPERSONATION_ENDED",
        actor_user=ending_user,
        organization=session.target_organization,
        target=("support.ImpersonationSession", session.pk),
        metadata={
            "session_id": session.session_id,
            "support_user_id": session.support_user_id,
            "target_user_id": session.target_user_id,
            "is_self_end": is_self_end,
            "end_reason": session.end_reason,
            "duration_seconds": (session.ended_at - session.started_at).total_seconds(),
        },
        request=request,
    )

    return session


def get_active_session(session_id: str) -> ImpersonationSession | None:
    """Look up an active impersonation session by its public session_id.

    Returns None if:
      - No session exists with that session_id, OR
      - The session has been explicitly ended, OR
      - The session has timed out (ends_at <= now)

    For timed-out sessions: this function does NOT mutate the row to fill
    in ended_at. That's a separate cleanup job (a future Celery beat task)
    so middleware stays read-only and fast. The session is correctly
    treated as not-active because of the ends_at check.
    """
    if not session_id:
        return None

    try:
        session = ImpersonationSession.objects.select_related(
            "support_user", "target_user", "target_organization", "target_membership"
        ).get(session_id=session_id)
    except ImpersonationSession.DoesNotExist:
        return None

    if not session.is_active:
        return None

    return session


def _safe_ip(request) -> str:
    """Extract a client IP without depending on the audit module's helper
    (avoids an import cycle if these services are imported at audit
    module-load time)."""
    if not hasattr(request, "META"):
        return ""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()[:64]
    return request.META.get("REMOTE_ADDR", "")[:64]
