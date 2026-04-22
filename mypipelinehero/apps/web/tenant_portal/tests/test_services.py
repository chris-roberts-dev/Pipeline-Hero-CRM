"""Tests for the tenant-portal complete_handoff service."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.common.services import AuthenticationError, ValidationError
from apps.platform.organizations.models import Membership, Organization
from apps.web.auth_portal.services import issue as issue_token
from apps.web.tenant_portal.services import complete_handoff

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_handoff_redis():
    import redis as redis_lib
    from django.conf import settings

    client = redis_lib.from_url(settings.HANDOFF_TOKEN_REDIS_URL, decode_responses=True)
    client.flushdb()
    yield
    client.flushdb()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="u@example.com", password="x" * 12)


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Alpha", slug="alpha")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Beta", slug="beta")


@pytest.fixture
def active_membership(db, user, org_a):
    return Membership.objects.create(
        user=user, organization=org_a, status=Membership.Status.ACTIVE
    )


@pytest.mark.django_db
class TestCompleteHandoff:
    def test_happy_path(self, user, org_a, active_membership):
        token = issue_token(user_id=user.pk, organization_id=org_a.pk)
        result = complete_handoff(token=token, expected_organization=org_a)
        assert result.user == user
        assert result.organization == org_a

    def test_invalid_token_raises_authentication_error(self, org_a):
        with pytest.raises(AuthenticationError):
            complete_handoff(token="bogus", expected_organization=org_a)

    def test_replayed_token_raises_authentication_error(
        self, user, org_a, active_membership
    ):
        # Issue, redeem once via complete_handoff, then try again.
        token = issue_token(user_id=user.pk, organization_id=org_a.pk)
        complete_handoff(token=token, expected_organization=org_a)
        with pytest.raises(AuthenticationError):
            complete_handoff(token=token, expected_organization=org_a)

    def test_token_for_different_org_raises_validation_error(
        self, user, org_a, org_b, active_membership
    ):
        # Issue token for org_a, then try to complete it on org_b's subdomain.
        # This is the cross-tenant misuse case from spec §9.4.
        token = issue_token(user_id=user.pk, organization_id=org_a.pk)
        with pytest.raises(ValidationError):
            complete_handoff(token=token, expected_organization=org_b)

    def test_membership_revoked_between_issue_and_redeem(
        self, user, org_a, active_membership
    ):
        # Spec §9.4: re-check access at redemption time, not just at issue.
        token = issue_token(user_id=user.pk, organization_id=org_a.pk)
        # Revoke membership after token is issued.
        active_membership.status = Membership.Status.SUSPENDED
        active_membership.save()
        with pytest.raises(ValidationError):
            complete_handoff(token=token, expected_organization=org_a)

    def test_user_deactivated_between_issue_and_redeem(
        self, user, org_a, active_membership
    ):
        token = issue_token(user_id=user.pk, organization_id=org_a.pk)
        user.is_active = False
        user.save()
        with pytest.raises(AuthenticationError):
            complete_handoff(token=token, expected_organization=org_a)
