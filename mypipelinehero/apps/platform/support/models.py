"""
Impersonation session model.

Spec §7.4 / §22.1 line 1561 call this `ImpersonationAuditLog`. We use
`ImpersonationSession` because the data shape captures a session lifecycle
(start, end, expiry) — "audit log" connotes append-only line items, but
this row is mutated when the session ends. The per-action audit semantics
land on `AuditEvent.on_behalf_of_user` instead.

Lifecycle:
  1. Support user calls `start_impersonation(...)` service. A row is
     created with started_at = now, ends_at = now + TTL, ended_at = NULL.
  2. While `ended_at IS NULL` and `now() < ends_at`, the session is active.
     The middleware reads the active row by session_id stored in the
     tenant-portal Django session.
  3. Calling `end_impersonation(...)` sets ended_at = now and end_reason.
     The row is preserved permanently for forensic purposes.
  4. A session that times out (ends_at < now without explicit end) is
     detected by the middleware and treated as ended; ended_at is filled
     in lazily on next request.

Tenancy:
  Not a TenantModel. The support user is platform-staff (no tenant
  membership of their own); the target_organization FK is what scopes
  the session's effects. Querysets use explicit `target_organization=`
  filtering rather than the default tenant manager.

Indexing:
  - (support_user, ended_at IS NULL) — "find this support user's active
    sessions" — answered by an index on support_user combined with a
    nullable filter on ended_at.
  - (target_user, ended_at IS NULL) — "is anyone currently impersonating
    this user?" — for support-tooling visibility.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generate_session_id() -> str:
    """Cryptographically random 32-character session identifier.

    Used as the public-facing session key stored in the tenant-portal
    Django session. We don't expose the row PK because PKs are
    enumerable and predictable; a random session_id forces the attacker
    to know the actual key, not just guess a low-numbered row.
    """
    return secrets.token_urlsafe(24)  # ~32 chars when base64-encoded


class ImpersonationSession(models.Model):
    """A record of one impersonation session, active or completed."""

    # Public-facing identifier stored in the tenant Django session. The
    # row PK is internal; session_id is what middleware looks up.
    session_id = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_session_id,
        editable=False,
    )

    # The support user who initiated the session. Must hold
    # support.impersonation.start at session-start time. PROTECT on
    # delete keeps the audit trail intact even if the support user is
    # later removed.
    support_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impersonation_sessions_initiated",
        help_text=_("The support user who started this session."),
    )

    # The user being impersonated. PROTECT for the same audit-trail reason.
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impersonation_sessions_received",
        help_text=_("The tenant user being impersonated."),
    )

    # Organization context. Impersonation always happens *as* a particular
    # membership in a particular org — even if the target user belongs to
    # multiple orgs, the support session is scoped to one. Required.
    target_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="impersonation_sessions",
        help_text=_("The organization whose tenant context this session enters."),
    )

    # The active membership being impersonated. Resolved at start time
    # and cached for fast middleware lookup. Could be re-derived from
    # (target_user, target_organization) but freezing it prevents drift
    # if the target user gains/loses memberships mid-session.
    target_membership = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.PROTECT,
        related_name="impersonation_sessions",
    )

    # Mandatory free-form rationale (spec §7.4 line 436).
    reason = models.TextField(
        help_text=_("Mandatory free-text reason for the impersonation."),
    )

    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ends_at = models.DateTimeField(
        help_text=_("Hard expiration. Sessions are not honored past this time."),
    )

    # NULL while session is active. Set on explicit end OR on lazy
    # detection by middleware that ends_at has passed.
    ended_at = models.DateTimeField(blank=True, null=True)

    # Who ended the session. NULL means timed-out (not explicitly ended).
    # Self-ending: ended_by == support_user. Force-ended by another support
    # user: ended_by != support_user (requires support.impersonation.end_any).
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="impersonation_sessions_ended",
    )

    end_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Free-form note when the session was ended explicitly."),
    )

    # Free-form metadata for forensic context (IP at start, user-agent,
    # request_id, etc.). Set by the start service.
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = _("impersonation session")
        verbose_name_plural = _("impersonation sessions")
        ordering = ["-started_at"]
        indexes = [
            # Active sessions for a support user.
            models.Index(
                fields=["support_user", "ended_at"],
                name="imp_support_active_idx",
            ),
            # Active sessions targeting a user (visibility from the user
            # side: "am I being impersonated right now?").
            models.Index(
                fields=["target_user", "ended_at"],
                name="imp_target_active_idx",
            ),
            # Default activity timeline.
            models.Index(
                fields=["target_organization", "-started_at"],
                name="imp_org_started_idx",
            ),
        ]

    def __str__(self) -> str:
        status = "active" if self.is_active else "ended"
        return (
            f"{self.support_user} → {self.target_user} "
            f"({self.target_organization.slug}, {status})"
        )

    @property
    def is_active(self) -> bool:
        """True if the session is currently honored.

        A session is active iff:
          - ended_at is NULL (not explicitly ended), AND
          - ends_at > now (not timed out)
        """
        if self.ended_at is not None:
            return False
        return self.ends_at > timezone.now()

    @property
    def is_expired(self) -> bool:
        """True if the session has timed out (without being explicitly ended)."""
        return self.ended_at is None and self.ends_at <= timezone.now()

    def time_remaining(self) -> timedelta:
        """How much time before the session expires. Negative if already
        expired. Used by the banner to show countdown."""
        return self.ends_at - timezone.now()
