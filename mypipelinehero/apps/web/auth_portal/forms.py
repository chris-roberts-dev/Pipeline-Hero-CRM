"""
Forms used by the auth portal.

Forms validate input shape and emit clean values; they do not enforce
business rules. Services own business rules.
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _


class LoginForm(forms.Form):
    """Central login form served on the root domain.

    Used by both tenant users and platform/support users — identity type
    is determined at authentication time, not by URL or form variant.
    """

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "username",
                "autofocus": "autofocus",
                "class": "form-control",
                "placeholder": "you@example.com",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "form-control",
            }
        ),
    )

    # `next` preserves a pre-login destination across the redirect chain.
    # Not used in M1 but accepted so the form is forward-compatible.
    next = forms.CharField(required=False, widget=forms.HiddenInput())


class OrganizationPickerForm(forms.Form):
    """Select which organization to enter, for multi-org users."""

    organization_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, allowed_org_ids: set[int] | None = None, **kwargs):
        """Constrain valid choices to the user's allowed organizations.

        `allowed_org_ids` is computed server-side from the user's active
        memberships. The form validates that the submitted id is a member
        of this set — defense in depth against a tampered POST.
        """
        super().__init__(*args, **kwargs)
        self._allowed_org_ids = allowed_org_ids or set()

    def clean_organization_id(self) -> int:
        value = self.cleaned_data["organization_id"]
        if value not in self._allowed_org_ids:
            raise forms.ValidationError(_("You are not a member of that organization."))
        return value
