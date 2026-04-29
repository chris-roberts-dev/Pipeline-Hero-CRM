"""
Support views.

Currently minimal: just `end_impersonation` so the banner's End button
works. The full start-impersonation flow is exposed by the platform
admin console (M2 step 6) — until then, sessions are started via the
Django shell or a management command for testing.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.platform.rbac.decorators import no_capability_required
from apps.platform.support.services import end_impersonation


@no_capability_required(
    reason=(
        "Self-end of an active impersonation session. The capability check "
        "happens inside the service (self-end always allowed for the "
        "session's support_user; force-end requires support.impersonation.end_any)."
    )
)
@login_required(login_url="landing:login")
@require_POST
def end_impersonation_view(request: HttpRequest) -> HttpResponse:
    """End the impersonation session active on this request, if any.

    Behavior:
      - If no impersonation is active on this request, redirect to the
        tenant dashboard. This is a no-op success path for stale clicks
        (banner already gone, etc.).
      - If active, end the session, clear the session-key from the
        Django session, and redirect to the dashboard.

    Note: ending impersonation does NOT log out the underlying support
    user. The next request from the support user (without impersonation)
    will route them through normal acting-membership resolution. They
    keep their root-domain session.
    """
    impersonation_session = getattr(request, "impersonation_session", None)

    if impersonation_session is not None:
        # ending_user is the user who is logged in — for self-end this is
        # the same as session.support_user. The service handles both.
        end_impersonation(
            session=impersonation_session,
            ending_user=request.user,
            end_reason="self_end_via_banner",
            request=request,
        )

        # Clean up the session-key so the next request doesn't try to
        # re-resolve a now-ended session.
        session_key = getattr(
            settings, "IMPERSONATION_SESSION_KEY", "impersonation_session_id"
        )
        request.session.pop(session_key, None)

    # Redirect to the tenant dashboard. Pass urlconf= explicitly because
    # this view's target lives in the tenant URLconf (config.urls_tenant)
    # — Django's reverse() defaults to ROOT_URLCONF unless TenancyMiddleware
    # has set the per-request urlconf via set_urlconf(). Being explicit
    # makes the view independent of middleware ordering and easier to test.
    dashboard_url = reverse("tenant_portal:dashboard", urlconf="config.urls_tenant")
    return HttpResponseRedirect(dashboard_url)
