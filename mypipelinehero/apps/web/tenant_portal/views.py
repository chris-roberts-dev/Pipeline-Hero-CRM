"""
Tenant portal views (tenant subdomain).

In M1 there's a handoff-completion endpoint, a tenant-local logout, and a
minimal dashboard stub so there's somewhere to land after handoff.

All views here REQUIRE `request.organization` to be set by TenancyMiddleware.
Requests to the tenant portal URLs over the root domain will hit the guard
at the top of each view and 404 out — tenant portal URLs are not valid on
the root domain.
"""

from __future__ import annotations

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.common.services import AuthenticationError, ValidationError
from apps.platform.audit.services import emit as audit_emit
from apps.web.tenant_portal.services import complete_handoff


def _require_tenant(request: HttpRequest):
    """Guard that ensures the request is on a tenant subdomain.

    Raises 404 if `request.organization` isn't set. This prevents
    tenant portal URLs from being reachable via the root domain.
    """
    org = getattr(request, "organization", None)
    if org is None:
        raise Http404("Tenant portal URLs are not served on the root domain.")
    return org


def handoff_completion(request: HttpRequest) -> HttpResponse:
    """Consume a handoff token and establish a tenant-local session.

    This is the only tenant-subdomain URL reachable without an existing
    tenant session — everything else requires auth.
    """
    organization = _require_tenant(request)

    token = request.GET.get("token", "")
    if not token:
        return render(request, "tenant_portal/handoff_failed.html", status=400)

    try:
        result = complete_handoff(token=token, expected_organization=organization)
    except AuthenticationError:
        audit_emit(
            event_type="HANDOFF_REJECTED_INVALID_TOKEN",
            organization=organization,
            request=request,
        )
        return render(request, "tenant_portal/handoff_failed.html", status=401)
    except ValidationError as exc:
        audit_emit(
            event_type="HANDOFF_REJECTED_MISMATCH",
            organization=organization,
            metadata={"reason": str(exc)},
            request=request,
        )
        return render(request, "tenant_portal/handoff_failed.html", status=403)

    # Establish a tenant-LOCAL session on this subdomain. Because
    # SESSION_COOKIE_DOMAIN is unset (spec §9.4), this cookie is scoped to
    # the exact host we're on and does not leak to siblings.
    django_login(request, result.user)

    # Stash the active organization id in the session so downstream views
    # can cheaply confirm "this session belongs on this subdomain" without
    # hitting the DB on every request.
    request.session["active_organization_id"] = organization.pk

    audit_emit(
        event_type="HANDOFF_COMPLETED",
        actor_user=result.user,
        organization=organization,
        request=request,
    )

    return redirect("tenant_portal:dashboard")


def dashboard(request: HttpRequest) -> HttpResponse:
    """Minimal landing page inside a tenant portal."""
    organization = _require_tenant(request)

    if not request.user.is_authenticated:
        # Tenant portal requires tenant-local auth. Send the user back to
        # root-domain login, which will re-issue a handoff token after auth.
        from django.conf import settings

        host = request.get_host()
        port = f":{host.split(':', 1)[1]}" if ":" in host else ""
        return redirect(f"{request.scheme}://{settings.ROOT_DOMAIN}{port}/login/")

    # Defense-in-depth: reject session that was established on a DIFFERENT
    # org's subdomain. Shouldn't happen (cookies are scoped per-host) but
    # catching it here turns a weird edge case into a hard redirect rather
    # than a silent cross-tenant flash.
    if request.session.get("active_organization_id") != organization.pk:
        django_logout(request)
        return redirect_to_root_login(request)

    return render(
        request,
        "tenant_portal/dashboard.html",
        {"organization": organization},
    )


def tenant_logout(request: HttpRequest) -> HttpResponse:
    """Tenant-local logout.

    Terminates ONLY the session on this subdomain. Does not affect the
    root-domain session or any other tenant sessions (spec §9.4).
    """
    _require_tenant(request)

    actor = request.user if request.user.is_authenticated else None
    organization = getattr(request, "organization", None)

    django_logout(request)

    if actor is not None:
        audit_emit(
            event_type="LOGOUT_TENANT",
            actor_user=actor,
            organization=organization,
            request=request,
        )

    return redirect_to_root_login(request)


def redirect_to_root_login(request: HttpRequest) -> HttpResponse:
    """Redirect the user to the root-domain login page, preserving port in dev."""
    from django.conf import settings

    host = request.get_host()
    port = f":{host.split(':', 1)[1]}" if ":" in host else ""
    return redirect(f"{request.scheme}://{settings.ROOT_DOMAIN}{port}/login/")
