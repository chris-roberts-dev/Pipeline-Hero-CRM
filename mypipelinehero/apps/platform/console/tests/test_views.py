"""Tests for the start-impersonation admin view.

The view is mounted at /admin/support/impersonationsession/start/ and
requires staff authentication. Most of the business logic is in the
service (covered by support/tests/test_services.py); this file covers
only the form-handling and template-rendering specific to the view.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.platform.organizations.models import Membership, Organization
from apps.platform.support.models import ImpersonationSession

User = get_user_model()


@pytest.fixture
def client(db):
    return Client()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="super@example.com",
        password="x" * 12,
    )


@pytest.fixture
def regular_staff_user(db):
    """A staff user (can access admin) who is NOT a superuser. Without
    the support.impersonation.start capability via a role, this user
    will fail the service-layer cap check."""
    return User.objects.create_user(
        email="staff@example.com",
        password="x" * 12,
        is_staff=True,
    )


@pytest.fixture
def target_user(db):
    return User.objects.create_user(email="alice@example.com", password="x" * 12)


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme")


@pytest.fixture
def target_membership(db, target_user, org):
    return Membership.objects.create(
        user=target_user, organization=org, status=Membership.Status.ACTIVE
    )


START_URL = "/admin/support/impersonationsession/start/"


@pytest.mark.django_db
class TestAccessControl:
    def test_anonymous_user_redirected_to_admin_login(self, client):
        response = client.get(START_URL)
        # staff_member_required redirects to admin login.
        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]

    def test_non_staff_user_redirected_to_admin_login(self, client, target_user):
        # target_user is not staff.
        client.force_login(target_user)
        response = client.get(START_URL)
        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]

    def test_staff_user_can_access_form(self, client, superuser):
        client.force_login(superuser)
        response = client.get(START_URL)
        assert response.status_code == 200
        # Form fields should be rendered.
        assert b"target_user" in response.content
        assert b"target_organization" in response.content
        assert b"reason" in response.content


@pytest.mark.django_db
class TestStartImpersonationSubmission:
    def test_valid_submission_creates_session(
        self, client, superuser, target_user, target_membership, org
    ):
        client.force_login(superuser)
        response = client.post(
            START_URL,
            {
                "target_user": target_user.pk,
                "target_organization": org.pk,
                "reason": "Investigating quote acceptance issue per ticket #1234",
            },
        )
        # Redirects to the new session's detail page.
        assert response.status_code == 302
        # Session was actually created.
        assert ImpersonationSession.objects.count() == 1
        session = ImpersonationSession.objects.get()
        assert session.support_user == superuser
        assert session.target_user == target_user
        assert session.target_organization == org
        assert session.is_active

    def test_short_reason_rejected_by_form(
        self, client, superuser, target_user, target_membership, org
    ):
        client.force_login(superuser)
        response = client.post(
            START_URL,
            {
                "target_user": target_user.pk,
                "target_organization": org.pk,
                "reason": "x",  # too short — form's min_length=10 catches this
            },
        )
        # Form re-rendered with errors, not a redirect.
        assert response.status_code == 200
        # No session created.
        assert ImpersonationSession.objects.count() == 0

    def test_no_membership_rejected_by_service(
        self, client, superuser, target_user, org
    ):
        # Target has no membership in this org.
        client.force_login(superuser)
        response = client.post(
            START_URL,
            {
                "target_user": target_user.pk,
                "target_organization": org.pk,
                "reason": "Investigating an issue per ticket #1234",
            },
        )
        # Form re-rendered with the service's ValidationError as a form error.
        assert response.status_code == 200
        assert b"active membership" in response.content
        assert ImpersonationSession.objects.count() == 0

    def test_non_superuser_staff_rejected_by_service(
        self, client, regular_staff_user, target_user, target_membership, org
    ):
        # Non-superuser staff. They can access the form (is_staff=True),
        # but the SERVICE's capability check rejects (no role grants the
        # support.impersonation.start cap, and they're not a superuser).
        client.force_login(regular_staff_user)
        response = client.post(
            START_URL,
            {
                "target_user": target_user.pk,
                "target_organization": org.pk,
                "reason": "Trying to impersonate without authorization",
            },
        )
        # Form re-rendered with the PermissionDeniedError as form error.
        assert response.status_code == 200
        assert b"support.impersonation.start" in response.content
        assert ImpersonationSession.objects.count() == 0
