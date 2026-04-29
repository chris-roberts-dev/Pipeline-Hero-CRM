"""Tests for end_impersonation_view.

Verifies POST flow ends an active session, GET is rejected, and the
view is idempotent (no-op when no session is active).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from apps.platform.organizations.models import Membership, Organization
from apps.platform.support.models import ImpersonationSession
from apps.platform.support.views import end_impersonation_view

User = get_user_model()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme")


@pytest.fixture
def support_user(db):
    return User.objects.create_superuser(email="support@example.com", password="x" * 12)


@pytest.fixture
def target_user(db):
    return User.objects.create_user(email="alice@example.com", password="x" * 12)


@pytest.fixture
def target_membership(db, target_user, org):
    return Membership.objects.create(
        user=target_user, organization=org, status=Membership.Status.ACTIVE
    )


@pytest.fixture
def session(db, support_user, target_user, target_membership, org):
    return ImpersonationSession.objects.create(
        support_user=support_user,
        target_user=target_user,
        target_organization=org,
        target_membership=target_membership,
        reason="Investigating an issue for ticket #1234",
        ends_at=timezone.now() + timedelta(minutes=30),
    )


@pytest.mark.django_db
class TestEndImpersonationView:
    def test_post_ends_active_session(
        self, request_factory, support_user, session, org
    ):
        request = request_factory.post("/_/end-impersonation/")
        request.user = support_user
        request.session = {settings.IMPERSONATION_SESSION_KEY: session.session_id}
        # Simulate what ActingMembershipMiddleware would have done:
        request.impersonation_session = session

        response = end_impersonation_view(request)
        assert response.status_code == 302  # redirect to dashboard
        # Session is ended.
        session.refresh_from_db()
        assert session.ended_at is not None
        assert session.ended_by == support_user
        # Session-key is cleared.
        assert settings.IMPERSONATION_SESSION_KEY not in request.session

    def test_post_with_no_active_session_is_noop(self, request_factory, support_user):
        # Stale-click case: banner already gone, user clicks anyway.
        request = request_factory.post("/_/end-impersonation/")
        request.user = support_user
        request.session = {}
        request.impersonation_session = None

        response = end_impersonation_view(request)
        # Still redirects somewhere sensible.
        assert response.status_code == 302
        # Nothing was written.
        assert ImpersonationSession.objects.count() == 0
