"""
ActingMembershipMiddleware: attach `request.acting_membership` to every
request. Honors active impersonation sessions.

For tenant-subdomain requests with an authenticated user, this resolves
the user's ACTIVE membership in `request.organization` and attaches it
as `request.acting_membership`. For root-domain requests or anonymous
users, the attribute is set to None.

When an impersonation session is active (the tenant Django session
contains a valid impersonation_session_id), this middleware:
  - Substitutes `request.acting_membership` to the IMPERSONATED user's
    membership instead of the support user's own
  - Attaches `request.impersonation_session` for the banner / context
    processor to read
  - Attaches `request.impersonation_target_user` for the audit emit()
    helper to consume automatically

This is the integration point for the M2 step 3 `@require_capability`
decorator — it reads `request.acting_membership` to evaluate
capabilities. The decorator never knows whether impersonation is active;
it just reads what's been attached.

Placement:
  After TenancyMiddleware (needs request.organization), after Django's
  AuthenticationMiddleware (needs request.user), and after
  SessionMiddleware (needs request.session). Defined in
  config/settings/base.py MIDDLEWARE order.
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class ActingMembershipMiddleware:
    """Resolve and attach `request.acting_membership`. Honors impersonation."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Default-initialize all attributes we add. Doing this here means
        # downstream code can always read the attributes without hasattr()
        # or try/except — they're guaranteed to exist on every request.
        request.acting_membership = None  # type: ignore[attr-defined]
        request.impersonation_session = None  # type: ignore[attr-defined]
        request.impersonation_target_user = None  # type: ignore[attr-defined]

        # Try to resolve impersonation first. If active, the impersonation
        # path completely overrides normal membership resolution — we use
        # the impersonated membership, not the support user's own.
        if not self._apply_impersonation(request):
            request.acting_membership = self._resolve_normal(request)  # type: ignore[attr-defined]

        return self.get_response(request)

    @staticmethod
    def _resolve_normal(request: HttpRequest):
        """Standard path: user's own active membership in the active org."""
        from apps.platform.rbac.evaluator import get_acting_membership

        user = getattr(request, "user", None)
        organization = getattr(request, "organization", None)
        return get_acting_membership(user=user, organization=organization)

    @staticmethod
    def _apply_impersonation(request: HttpRequest) -> bool:
        """Check for and apply an active impersonation session.

        Returns True if impersonation was applied (caller should not
        run normal resolution), False otherwise.

        Failure modes (all return False, none raise):
          - No session attribute on the request (e.g., root domain may
            not have SessionMiddleware processing if URL is excluded)
          - No session_id stored
          - Session not found in DB
          - Session ended or expired (implicitly via get_active_session)
          - Session belongs to a different organization than current
            request — this is defense-in-depth in case the support user
            navigated to another tenant subdomain while a session was
            active. The session is silently ignored on the wrong org.
        """
        # Local imports for the same reasons as elsewhere in this module.
        from django.conf import settings

        from apps.platform.support.services import get_active_session

        # SessionMiddleware always runs before us per MIDDLEWARE order, but
        # belt-and-braces: without a session, no impersonation.
        if not hasattr(request, "session"):
            return False

        session_key = getattr(
            settings, "IMPERSONATION_SESSION_KEY", "impersonation_session_id"
        )
        session_id = request.session.get(session_key)
        if not session_id:
            return False

        impersonation = get_active_session(session_id)
        if impersonation is None:
            # Session expired or ended. Clean up the dangling session-key
            # so subsequent requests don't keep doing this DB lookup.
            try:
                del request.session[session_key]
            except KeyError:
                pass
            return False

        # Org match check. If the support user navigated to a DIFFERENT
        # tenant while a session was active, ignore the impersonation
        # there. This shouldn't happen in normal flow — tenant Django
        # sessions are scoped per-host — but the defensive check costs
        # us nothing.
        organization = getattr(request, "organization", None)
        if (
            organization is None
            or organization.pk != impersonation.target_organization_id
        ):
            return False

        # Apply impersonation. The acting_membership is the IMPERSONATED
        # user's membership; the request.user remains the support user
        # for auth purposes. The audit layer reads
        # request.impersonation_target_user.
        request.acting_membership = impersonation.target_membership  # type: ignore[attr-defined]
        request.impersonation_session = impersonation  # type: ignore[attr-defined]
        request.impersonation_target_user = impersonation.target_user  # type: ignore[attr-defined]
        return True


class PermissionDeniedMiddleware:
    """Translate domain `PermissionDeniedError` exceptions into HTTP 403.

    The `@require_capability` decorator and service-layer code raise
    `PermissionDeniedError` (our domain exception) when authorization
    fails. Without this middleware, those propagate uncaught and Django
    returns a 500.

    Why a middleware rather than try/except in views?
      - Single chokepoint. Every view, every service-layer raise, every
        decorator gets the same handling.
      - Testable in isolation.
      - Lets the decorator stay a pure capability check rather than
        coupling it to HTTP semantics.

    Logging:
      Denials are logged at INFO. Mass-deny patterns (probing,
      misconfigured roles) become observable without flooding ERROR.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception):
        # Local import — keep the exceptions module from being eagerly
        # imported during Django's middleware-class loading.
        from apps.common.services.exceptions import PermissionDeniedError

        if not isinstance(exception, PermissionDeniedError):
            return None  # let Django (or other middleware) handle it

        return self._render_403(request, str(exception))

    @staticmethod
    def _render_403(request: HttpRequest, reason: str) -> HttpResponse:
        # Local imports for the same reason as above.
        import logging

        from django.shortcuts import render

        logger = logging.getLogger("apps.platform.rbac.middleware")
        # Log who, what, where for support-ability. Don't include the
        # full reason in production logs at DEBUG-level visibility — it
        # may include capability codes we don't want in log aggregation.
        logger.info(
            "permission_denied user=%s membership=%s path=%s reason=%s",
            getattr(request.user, "pk", None),
            getattr(getattr(request, "acting_membership", None), "pk", None),
            request.path,
            reason,
        )

        return render(
            request,
            "rbac/403.html",
            {"reason": reason},
            status=403,
        )
