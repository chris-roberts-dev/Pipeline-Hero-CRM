"""
Auth portal views (root domain).

These sit between the login landing page and the tenant portal:
  - `pick_organization`: multi-org users choose where to go
  - `issue_handoff`: server-side redirect that mints a handoff token and
    sends the browser to the tenant subdomain

Service-layer discipline: token issuance, membership validation, and audit
emission all live in services. Views translate the HTTP layer only.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render

from apps.platform.accounts.services import user_can_access_org
from apps.platform.audit.services import emit as audit_emit
from apps.platform.organizations.models import Membership, Organization
from apps.web.auth_portal.forms import OrganizationPickerForm
from apps.web.auth_portal.services import issue as issue_handoff_token


def _tenant_portal_url(organization: Organization, token: str, request: HttpRequest) -> str:
    """Build the tenant-subdomain URL for handoff completion.

    In dev the port is preserved (e.g. :80, :8000). In prod there's no port
    in the URL because nginx/ingress terminates on 80/443.
    """
    host = f"{organization.slug}.{settings.ROOT_DOMAIN}"
    # Preserve port from the current request so dev environments work.
    # `get_host()` includes port when present.
    current_host = request.get_host()
    if ":" in current_host:
        port = current_host.split(":", 1)[1]
        host = f"{host}:{port}"
    return f"{request.scheme}://{host}/auth/handoff?token={token}"


@login_required(login_url="landing:login")
def pick_organization(request: HttpRequest) -> HttpResponse:
    """Multi-org users choose which tenant to enter."""
    memberships = (
        Membership.objects.filter(
            user=request.user,
            status=Membership.Status.ACTIVE,
            organization__status=Organization.Status.ACTIVE,
        )
        .select_related("organization")
        .order_by("organization__name")
    )
    allowed_ids = {m.organization_id for m in memberships}

    if request.method == "GET":
        return render(
            request,
            "auth_portal/pick_organization.html",
            {"memberships": memberships},
        )

    form = OrganizationPickerForm(request.POST, allowed_org_ids=allowed_ids)
    if not form.is_valid():
        return render(
            request,
            "auth_portal/pick_organization.html",
            {"memberships": memberships, "form": form},
            status=400,
        )

    from django.urls import reverse

    return redirect(
        f"{reverse('auth_portal:issue_handoff')}?org={form.cleaned_data['organization_id']}"
    )


@login_required(login_url="landing:login")
def issue_handoff(request: HttpRequest) -> HttpResponse:
    """Mint a handoff token for the selected org and redirect to tenant subdomain.

    GET-only: this endpoint is hit via redirect from the login view (single-org
    users) or the org picker (multi-org users). Idempotent in the sense that
    each call issues a new token; tokens are single-use and 60s so stale
    ones self-expire.
    """
    org_id_raw = request.GET.get("org")
    if not org_id_raw:
        return HttpResponseBadRequest("Missing org parameter.")
    try:
        org_id = int(org_id_raw)
    except ValueError:
        return HttpResponseBadRequest("Invalid org parameter.")

    try:
        organization = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
        return HttpResponseBadRequest("Unknown organization.")

    # Double-check access server-side. The form validates this too, but
    # the handoff URL is reachable directly, so we re-verify here.
    if not user_can_access_org(user=request.user, organization=organization):
        audit_emit(
            event_type="HANDOFF_DENIED_NO_MEMBERSHIP",
            actor_user=request.user,
            organization=organization,
            request=request,
        )
        return render(request, "landing/no_access.html", status=403)

    token = issue_handoff_token(
        user_id=request.user.pk,
        organization_id=organization.pk,
    )
    audit_emit(
        event_type="HANDOFF_TOKEN_ISSUED",
        actor_user=request.user,
        organization=organization,
        request=request,
    )

    return redirect(_tenant_portal_url(organization, token, request))
