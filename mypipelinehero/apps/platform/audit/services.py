"""
Audit event emission helper.

Services call `emit()` to record auditable actions. Keeping emission in one
place makes it trivial to:
  - add cross-cutting metadata (release version, hostname, etc.) in one spot
  - swap the backend later (async emission via outbox in M4+)
  - enforce the masking rules from spec §26.1A at a single chokepoint

Usage:
    from apps.platform.audit.services import emit

    emit(
        event_type="LOGIN_SUCCESS",
        actor_user=user,
        organization=None,
        request=request,  # populates ip/user_agent from request headers
        metadata={"method": "password"},
    )

Emission is synchronous in M1. In M4 we introduce the outbox pattern so
emission is guaranteed to persist in the same transaction as the state
change being audited. For now the audit row is written immediately; if the
surrounding transaction rolls back, the audit row goes with it (which is
fine — we don't want audit entries for actions that never happened).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.platform.audit.models import AuditEvent


def emit(
    *,
    event_type: str,
    actor_user: Any | None = None,
    on_behalf_of_user: Any | None = None,
    organization: Any | None = None,
    target: tuple[str, Any] | None = None,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
    request: HttpRequest | None = None,
) -> AuditEvent:
    """Record an auditable action.

    All arguments are keyword-only to prevent positional confusion between
    the many optional identity fields.

    Args:
        event_type: Convention `DOMAIN_ACTION`, e.g. `LOGIN_SUCCESS`.
        actor_user: Who performed the action. NULL for system-generated events.
        on_behalf_of_user: The impersonated user (only set during impersonation).
        organization: Tenant scope. NULL for platform-global events.
        target: Loose reference as ``("app_label.ModelName", pk)``. NOT a
            foreign key — audit persists even if the target is later deleted.
        before / after: Optional state snapshots. Emitters MUST mask sensitive
            fields per spec §26.1A before passing them here.
        metadata: Free-form JSON for event-specific context.
        request: If passed, IP and user-agent are extracted for attribution.

    Returns the persisted AuditEvent.
    """
    target_label = ""
    target_pk = ""
    if target is not None:
        target_label, pk = target
        target_pk = str(pk)

    ip_address = ""
    user_agent = ""
    if request is not None:
        ip_address = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]

        # Auto-resolve impersonation context from the request if the caller
        # didn't explicitly pass on_behalf_of_user. This means every
        # service-layer emit() during an impersonation session correctly
        # records both identities without each caller having to remember.
        # The middleware (rbac.middleware.ActingMembershipMiddleware) sets
        # `request.impersonation_target_user` when an impersonation session
        # is active; otherwise the attribute is absent (None).
        if on_behalf_of_user is None:
            on_behalf_of_user = getattr(request, "impersonation_target_user", None)

    return AuditEvent.objects.create(
        event_type=event_type,
        actor_user=actor_user,
        on_behalf_of_user=on_behalf_of_user,
        organization=organization,
        target_model_label=target_label,
        target_pk=target_pk,
        before=before,
        after=after,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def _client_ip(request: HttpRequest) -> str:
    """Extract the client IP from a request.

    Trusts `X-Forwarded-For` because nginx sits in front of Django in this
    deployment. In prod the ingress controller sets this; in dev our
    compose nginx does. If you deploy without a trusted proxy in front,
    revisit this — XFF is trivially spoofable by direct-to-app connections.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        # XFF may be a comma-separated chain; the leftmost is the original client.
        return xff.split(",")[0].strip()[:64]
    return request.META.get("REMOTE_ADDR", "")[:64]
