"""Tests for the RBAC middlewares.

ActingMembershipMiddleware: attaches request.acting_membership.
PermissionDeniedMiddleware: translates PermissionDeniedError to HTTP 403.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.common.services.exceptions import PermissionDeniedError
from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.middleware import (
    ActingMembershipMiddleware,
    PermissionDeniedMiddleware,
)

User = get_user_model()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="alice@example.com", password="x" * 12)


@pytest.fixture
def membership(db, user, org):
    return Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )


# ---------------------------------------------------------------------------
# ActingMembershipMiddleware
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestActingMembershipMiddleware:
    def test_attaches_acting_membership_for_authenticated_user_in_org(
        self, request_factory, user, membership, org
    ):
        captured = {}

        def get_response(request):
            captured["acting_membership"] = request.acting_membership
            return "ok"

        mw = ActingMembershipMiddleware(get_response)
        request = request_factory.get("/")
        request.user = user
        request.organization = org

        result = mw(request)
        assert result == "ok"
        assert captured["acting_membership"] == membership

    def test_attribute_is_none_for_anonymous_user(self, request_factory, org):
        captured = {}

        def get_response(request):
            captured["acting_membership"] = request.acting_membership
            return "ok"

        mw = ActingMembershipMiddleware(get_response)
        request = request_factory.get("/")
        request.user = AnonymousUser()
        request.organization = org

        mw(request)
        assert captured["acting_membership"] is None

    def test_attribute_is_none_when_no_organization(self, request_factory, user):
        captured = {}

        def get_response(request):
            captured["acting_membership"] = request.acting_membership
            return "ok"

        mw = ActingMembershipMiddleware(get_response)
        request = request_factory.get("/")
        request.user = user
        request.organization = None

        mw(request)
        assert captured["acting_membership"] is None

    def test_attribute_is_none_when_membership_inactive(
        self, request_factory, user, org
    ):
        # Suspended membership should not be the acting membership.
        Membership.objects.create(
            user=user, organization=org, status=Membership.Status.SUSPENDED
        )
        captured = {}

        def get_response(request):
            captured["acting_membership"] = request.acting_membership
            return "ok"

        mw = ActingMembershipMiddleware(get_response)
        request = request_factory.get("/")
        request.user = user
        request.organization = org

        mw(request)
        assert captured["acting_membership"] is None


# ---------------------------------------------------------------------------
# PermissionDeniedMiddleware
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPermissionDeniedMiddleware:
    def test_permission_denied_returns_403(self, request_factory, user):
        # process_exception is called with the exception; if a view raised
        # PermissionDeniedError, the middleware should render a 403.
        mw = PermissionDeniedMiddleware(get_response=lambda r: None)
        request = request_factory.get("/")
        request.user = user

        exc = PermissionDeniedError("test denial")
        response = mw.process_exception(request, exc)

        assert response is not None
        assert response.status_code == 403

    def test_other_exceptions_pass_through(self, request_factory, user):
        # Non-PermissionDeniedError exceptions should NOT be intercepted —
        # process_exception returns None to let Django's default handling
        # (or the next middleware) deal with it.
        mw = PermissionDeniedMiddleware(get_response=lambda r: None)
        request = request_factory.get("/")
        request.user = user

        exc = ValueError("something else")
        response = mw.process_exception(request, exc)

        assert response is None

    def test_response_includes_reason_text(self, request_factory, user):
        mw = PermissionDeniedMiddleware(get_response=lambda r: None)
        request = request_factory.get("/")
        request.user = user

        exc = PermissionDeniedError("Capability 'quotes.approve' is required.")
        response = mw.process_exception(request, exc)

        # Reason is rendered in the template.
        assert b"quotes.approve" in response.content


# ---------------------------------------------------------------------------
# Settings wiring sanity check
# ---------------------------------------------------------------------------


class TestMiddlewareConfiguration:
    """Verify both RBAC middlewares are listed in MIDDLEWARE in the right
    order. This catches accidental removal or reordering — the middlewares
    only work if both are present and ActingMembershipMiddleware runs
    after AuthenticationMiddleware and TenancyMiddleware."""

    def test_acting_membership_middleware_is_installed(self, settings):
        assert (
            "apps.platform.rbac.middleware.ActingMembershipMiddleware"
            in settings.MIDDLEWARE
        )

    def test_permission_denied_middleware_is_installed(self, settings):
        assert (
            "apps.platform.rbac.middleware.PermissionDeniedMiddleware"
            in settings.MIDDLEWARE
        )

    def test_acting_membership_runs_after_auth_and_tenancy(self, settings):
        # ActingMembershipMiddleware needs request.user (set by
        # AuthenticationMiddleware) and request.organization (set by
        # TenancyMiddleware). Order matters; this guards against future
        # accidental reordering.
        mw = settings.MIDDLEWARE
        auth_idx = mw.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        tenancy_idx = mw.index("apps.common.tenancy.middleware.TenancyMiddleware")
        acting_idx = mw.index(
            "apps.platform.rbac.middleware.ActingMembershipMiddleware"
        )
        assert acting_idx > auth_idx
        assert acting_idx > tenancy_idx
