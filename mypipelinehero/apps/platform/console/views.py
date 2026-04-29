"""
Start-impersonation admin view.

Provides a form-based UI for support staff to begin an impersonation
session. Lives at `/admin/support/impersonationsession/start/` and is
linked from the ImpersonationSession changelist.

Why a custom admin view rather than overriding the standard `add_view`?
  - The "add" form would expose every model field (target_membership,
    ends_at, ended_at, etc.). We want a clean form that takes only the
    inputs the SERVICE needs (target user, target org, reason) and lets
    the service compute the rest.
  - We MUST go through `start_impersonation()` so the audit emission and
    target-membership resolution happen in one transactional unit. A raw
    model save would skip those.

Auth:
  Standard admin auth (is_staff). The service layer's capability check
  is the real authorization gate — this view just provides the form.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.common.services import PermissionDeniedError, ValidationError
from apps.platform.accounts.models import User
from apps.platform.organizations.models import Organization
from apps.platform.rbac.decorators import no_capability_required
from apps.platform.support.services import start_impersonation


class StartImpersonationForm(forms.Form):
    """Inputs for the start-impersonation flow.

    Deliberately minimal: just the three things the service needs.
    Everything else (TTL, session_id, target_membership) is computed.
    """

    target_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("email"),
        help_text="The tenant user to impersonate. Active users only.",
    )
    target_organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(
            status=Organization.Status.ACTIVE
        ).order_by("name"),
        help_text="The organization context for this session.",
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        min_length=10,
        max_length=2000,
        help_text=(
            "Mandatory free-text reason. Will be stored on the audit "
            "record and visible to the impersonated user's organization "
            "admins. Be specific."
        ),
    )


@no_capability_required(
    reason=(
        "Mounted under /admin/ which is staff-only via @staff_member_required. "
        "The real authorization gate is inside the service "
        "(start_impersonation enforces support.impersonation.start)."
    )
)
@staff_member_required(login_url="/admin/login/")
def start_impersonation_view(request: HttpRequest) -> HttpResponse:
    """Render and process the start-impersonation form."""

    if request.method == "POST":
        form = StartImpersonationForm(request.POST)
        if form.is_valid():
            try:
                session = start_impersonation(
                    support_user=request.user,
                    target_user=form.cleaned_data["target_user"],
                    target_organization=form.cleaned_data["target_organization"],
                    reason=form.cleaned_data["reason"],
                    request=request,
                )
            except PermissionDeniedError as exc:
                # User can't even be here without is_staff, but the
                # capability gate is a stronger check (only superusers
                # pass in v1). Surface as a form error.
                form.add_error(None, str(exc))
            except ValidationError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Impersonation session started for "
                    f"{session.target_user.email} in "
                    f"{session.target_organization.name}. "
                    f"Visit the tenant subdomain to use it.",
                )
                # Redirect to the session's detail page so support staff
                # can copy the session_id or verify the audit record.
                return redirect(
                    reverse(
                        "console:support_impersonationsession_change",
                        args=[session.pk],
                    )
                )
    else:
        form = StartImpersonationForm()

    return render(
        request,
        "console/start_impersonation.html",
        {
            "form": form,
            "title": "Start Impersonation Session",
            # `site_header` etc. come from the AdminSite; the template
            # extends admin/base_site.html so they render in context.
            "site_header": "MyPipelineHero Platform Console",
            "has_permission": True,  # required by admin/base_site.html
        },
    )
