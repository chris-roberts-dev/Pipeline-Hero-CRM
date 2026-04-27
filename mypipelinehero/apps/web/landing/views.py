"""
Landing page views (root domain).

In M1 this is just the login page. A proper marketing site is a Phase 2
concern (spec §9.1). The landing view is thin: it delegates authentication
to the auth-portal service and routing to the org-picker view.
"""

from __future__ import annotations

from django.contrib.auth import login as django_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.common.services import AuthenticationError
from apps.platform.accounts.services import login_with_password
from apps.platform.audit.services import emit as audit_emit
from apps.platform.rbac.decorators import no_capability_required
from apps.web.auth_portal.forms import LoginForm


def _reject_tenant_subdomain(request: HttpRequest) -> HttpResponse | None:
    """Guard: the login landing page lives ONLY on the root domain.

    If a user lands on `{slug}.mypipelinehero.localhost/` they get redirected
    to the root-domain login rather than being served a second copy of the
    form. Prevents confusion and ensures the login session is always
    established against the root domain.
    """
    if getattr(request, "organization", None) is not None:
        from django.conf import settings

        root_url = f"{request.scheme}://{settings.ROOT_DOMAIN}"
        if ":" in request.get_host():
            port = request.get_host().split(":", 1)[1]
            root_url = f"{request.scheme}://{settings.ROOT_DOMAIN}:{port}"
        return redirect(f"{root_url}/login/")
    return None


@no_capability_required(reason="Pre-authentication: login form. Cap gate would be circular.")
def login_view(request: HttpRequest) -> HttpResponse:
    """GET: render the login form. POST: authenticate and route."""
    if (redirect_resp := _reject_tenant_subdomain(request)) is not None:
        return redirect_resp

    if request.method == "GET":
        return render(request, "landing/login.html", {"form": LoginForm()})

    form = LoginForm(request.POST)
    if not form.is_valid():
        return render(request, "landing/login.html", {"form": form}, status=400)

    try:
        result = login_with_password(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
    except AuthenticationError as exc:
        audit_emit(
            event_type="LOGIN_FAILURE",
            actor_user=None,
            metadata={"email": form.cleaned_data["email"]},
            request=request,
        )
        # Re-render with a generic error. Do not expose whether the email
        # is registered — same message for unknown email and wrong password.
        form.add_error(None, str(exc))
        return render(request, "landing/login.html", {"form": form}, status=401)

    # Establish the root-domain session. This is a separate session from
    # any future tenant-local sessions (spec §9.4 — root logout terminates
    # the root session only).
    django_login(request, result.user)
    audit_emit(
        event_type="LOGIN_SUCCESS",
        actor_user=result.user,
        metadata={"method": "password"},
        request=request,
    )

    # Route based on membership count.
    if result.default_org is not None and not result.selectable_orgs.exists():
        # Single-org user: go straight to handoff.
        return redirect(
            f"{reverse('auth_portal:issue_handoff')}?org={result.default_org.pk}"
        )

    if result.selectable_orgs.exists():
        return redirect("auth_portal:pick_organization")

    if result.is_platform_user:
        # Platform user with no org memberships — M2 will point this at the
        # platform console. For now, a placeholder page.
        return redirect("landing:platform_console")

    # No memberships, no platform access — dead end. Render a friendly error.
    return render(request, "landing/no_access.html", status=403)


@no_capability_required(
    reason="Placeholder; M2 will introduce a platform-staff capability and gate this."
)
def platform_console_placeholder(request: HttpRequest) -> HttpResponse:
    """Placeholder target for platform users until M2 builds the real console."""
    return render(request, "landing/platform_console_placeholder.html")


@no_capability_required(reason="Authenticated dead-end page; user has no org access.")
def no_access_view(request: HttpRequest) -> HttpResponse:
    """Rendered when an authenticated user has no accessible org and isn't staff."""
    return render(request, "landing/no_access.html", status=403)


@no_capability_required(reason="Authenticated logout; cap gate would prevent escape.")
def logout_view(request: HttpRequest) -> HttpResponse:
    """Root-domain logout.

    Per spec §9.4, this terminates ONLY the root-domain session. Any active
    tenant-local sessions on {slug}.mypipelinehero.localhost remain until
    those tenants' own /logout endpoints are hit (or their sessions expire).

    We do invalidate the handoff path — issuing new handoff tokens requires
    re-authenticating on the root domain, which is the desired semantics.
    """
    from django.contrib.auth import logout as django_logout

    actor = request.user if request.user.is_authenticated else None
    django_logout(request)
    if actor is not None:
        audit_emit(
            event_type="LOGOUT_ROOT",
            actor_user=actor,
            request=request,
        )
    return redirect("landing:login")
