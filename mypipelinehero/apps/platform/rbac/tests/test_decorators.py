"""Tests for apps.platform.rbac.decorators."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.common.services.exceptions import PermissionDeniedError
from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.decorators import (
    get_required_capability,
    is_capability_exempt,
    no_capability_required,
    require_capability,
)
from apps.platform.rbac.models import MembershipRole, Role
from apps.platform.rbac.services import seed_default_roles_for_org

User = get_user_model()


@pytest.fixture
def org(db):
    org = Organization.objects.create(name="Acme", slug="acme")
    seed_default_roles_for_org(org)
    return org


@pytest.fixture
def user(db):
    return User.objects.create_user(email="alice@example.com", password="x" * 12)


@pytest.fixture
def membership(db, user, org):
    return Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )


@pytest.fixture
def membership_with_owner(db, membership, org):
    owner_role = Role.objects.for_org(org).get(system_key=Role.SystemKey.OWNER)
    MembershipRole.objects.create(
        organization=org, membership=membership, role=owner_role
    )
    return membership


@pytest.fixture
def request_factory():
    return RequestFactory()


# ---------------------------------------------------------------------------
# @require_capability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRequireCapability:
    def test_grants_when_membership_holds_capability(
        self, user, membership_with_owner, request_factory
    ):
        @require_capability("leads.view")
        def view(request):
            return "ok"

        request = request_factory.get("/")
        request.user = user
        request.acting_membership = membership_with_owner

        assert view(request) == "ok"

    def test_denies_when_membership_lacks_capability(
        self, user, membership, request_factory
    ):
        @require_capability("leads.view")
        def view(request):
            return "ok"

        request = request_factory.get("/")
        request.user = user
        request.acting_membership = membership  # no roles assigned

        with pytest.raises(PermissionDeniedError, match="leads.view"):
            view(request)

    def test_denies_when_acting_membership_missing_from_request(
        self, user, request_factory
    ):
        # If middleware didn't set request.acting_membership, the decorator
        # treats it as "no active membership" and denies. Fail-closed.
        @require_capability("leads.view")
        def view(request):
            return "ok"

        request = request_factory.get("/")
        request.user = user
        # Deliberately do NOT set request.acting_membership.

        with pytest.raises(PermissionDeniedError):
            view(request)

    def test_marker_is_set_on_decorated_view(self):
        @require_capability("quotes.approve")
        def view(request):
            return "ok"

        assert get_required_capability(view) == "quotes.approve"

    def test_decorated_view_passes_through_args(
        self, user, membership_with_owner, request_factory
    ):
        @require_capability("leads.view")
        def view(request, item_id, *, extra=None):
            return (item_id, extra)

        request = request_factory.get("/")
        request.user = user
        request.acting_membership = membership_with_owner

        assert view(request, 42, extra="x") == (42, "x")


# ---------------------------------------------------------------------------
# @no_capability_required
# ---------------------------------------------------------------------------


class TestNoCapabilityRequired:
    def test_marker_set_with_reason(self):
        @no_capability_required(reason="Public landing")
        def view(request):
            return "ok"

        assert is_capability_exempt(view) is True

    def test_view_executes_normally(self):
        @no_capability_required(reason="Public landing")
        def view(request):
            return "ok"

        # No request setup needed — the decorator doesn't gate, just marks.
        assert view(None) == "ok"

    def test_empty_reason_raises(self):
        with pytest.raises(ValueError, match="non-empty reason"):
            @no_capability_required(reason="")
            def view(request):
                return "ok"

    def test_unmarked_view_is_not_exempt(self):
        def view(request):
            return "ok"

        assert is_capability_exempt(view) is False
        assert get_required_capability(view) is None


# ---------------------------------------------------------------------------
# Marker introspection
# ---------------------------------------------------------------------------


class TestMarkerIntrospection:
    def test_get_required_capability_returns_none_for_undecorated(self):
        def view(request):
            return "ok"
        assert get_required_capability(view) is None

    def test_is_capability_exempt_returns_false_for_undecorated(self):
        def view(request):
            return "ok"
        assert is_capability_exempt(view) is False

    def test_get_required_capability_walks_wrapper_chain(self):
        # @require_capability uses functools.wraps, so the marker is on
        # the wrapper. Confirm the helper finds it through __wrapped__.
        @require_capability("leads.view")
        def view(request):
            return "ok"

        # Wrap one more time to simulate stacking decorators.
        from functools import wraps

        @wraps(view)
        def outer(request):
            return view(request)

        assert get_required_capability(outer) == "leads.view"
