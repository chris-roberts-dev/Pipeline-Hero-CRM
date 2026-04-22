"""
AuditEvent — append-only audit log.

Spec §26 makes this a first-class domain: every significant state change,
authentication event, capability change, impersonation start/end, pricing
override, etc. must produce an AuditEvent. The model is intentionally
permissive on payload shape — different event types record different data —
and strict on attribution (who, when, on what, under which org).

Design notes:
  - JSONField for `before`/`after` snapshots. Spec §26.1A requires masking of
    sensitive fields before persistence — that responsibility lives in the
    emitter (service layer), not here. This model trusts what it's given.
  - `on_behalf_of_user` is populated for impersonation sessions (spec §7.4).
    Both actor AND impersonated identities are preserved so audits can be
    attributed correctly.
  - Organization is nullable because some events are genuinely platform-global
    (e.g. creation of a new Organization itself, super-admin login). We do
    NOT use TenantModel here — the FK is explicit and nullable.
  - `target_model_label` + `target_pk` is a loose reference to the record
    the event concerns. We deliberately do NOT use GenericForeignKey (spec
    §5.6 forbids it for cross-domain linkage). This is not a queryable
    relation; it's audit metadata for human investigation.
  - Append-only is enforced via service-layer discipline, not DB triggers,
    in v1. A no-update/no-delete policy is documented here; we consider a
    trigger-based enforcement in later phases if needed.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditEvent(models.Model):
    """An immutable record of a single auditable action.

    Write-only from application code. Per spec §26.1A this model must never be
    updated or deleted after insert. Retention and export policy are defined
    separately and not enforced here.
    """

    # `event_type` is a free-form string code like 'QUOTE_ACCEPTED', 'LOGIN_SUCCESS',
    # 'IMPERSONATION_STARTED'. We keep it as a CharField rather than a TextChoices
    # enum because event types are added in nearly every milestone and
    # maintaining a single central enum becomes painful. Each domain's service
    # layer owns the codes it emits and the format follows `DOMAIN_ACTION` convention.
    event_type = models.CharField(max_length=80, db_index=True)

    # The acting user. NULL for system-generated events (Celery beat tasks,
    # startup hooks, etc.) — those are attributed to a well-known "SYSTEM"
    # event_type marker by convention instead.
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
        help_text=_("The user who performed the action, or NULL for system events."),
    )

    # Populated only during impersonation. When present, `actor_user` is the
    # support user who initiated impersonation and this field is the tenant
    # user being impersonated (spec §10.2 step 2).
    on_behalf_of_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
    )

    # Organization the event is scoped to. Nullable for genuinely global
    # events (org creation, super-admin platform actions). NOT a TenantModel
    # because these semantics don't fit.
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
    )

    # Loose reference to the affected object, for human investigation only.
    # NOT a GFK (spec §5.6). Emitters pass something like ('quotes.QuoteVersion', 42).
    target_model_label = models.CharField(max_length=100, blank=True)
    target_pk = models.CharField(max_length=64, blank=True)

    # Before/after snapshots and any contextual metadata. Emitters are
    # responsible for masking/redacting sensitive fields before passing the
    # payload (spec §26.1A).
    before = models.JSONField(blank=True, null=True)
    after = models.JSONField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    # Captured for request-attribution purposes. IP is string-typed rather
    # than GenericIPAddressField to accept X-Forwarded-For edge cases.
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("audit event")
        verbose_name_plural = _("audit events")
        ordering = ["-created_at"]
        indexes = [
            # Investigation queries: "show me all events for this org, newest first".
            models.Index(
                fields=["organization", "-created_at"],
                name="audit_org_created_idx",
            ),
            # "All actions a user took" and "all events about a user".
            models.Index(
                fields=["actor_user", "-created_at"],
                name="audit_actor_created_idx",
            ),
            # Type-filtered views ("show all QUOTE_ACCEPTED events").
            models.Index(fields=["event_type", "-created_at"], name="audit_type_created_idx"),
        ]

    def __str__(self) -> str:
        parts = [self.event_type]
        if self.organization_id:
            parts.append(f"org={self.organization_id}")
        if self.actor_user_id:
            parts.append(f"actor={self.actor_user_id}")
        return " ".join(parts)
