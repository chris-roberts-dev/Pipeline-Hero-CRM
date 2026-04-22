"""Tests for the auth service (login_with_password, routing decisions)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.common.services import AuthenticationError
from apps.platform.accounts.services import (
    login_with_password,
    user_can_access_org,
)
from apps.platform.organizations.models import Membership, Organization

User = get_user_model()

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password=PASSWORD)


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Alpha", slug="alpha")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Beta", slug="beta")


@pytest.mark.django_db
class TestLoginWithPassword:
    def test_valid_credentials_return_user(self, user):
        result = login_with_password(email=user.email, password=PASSWORD)
        assert result.user == user

    def test_wrong_password_raises(self, user):
        with pytest.raises(AuthenticationError):
            login_with_password(email=user.email, password="wrong")

    def test_unknown_email_raises_same_error(self):
        # Must be the same exception type as wrong-password to avoid enumeration.
        with pytest.raises(AuthenticationError):
            login_with_password(email="nobody@example.com", password=PASSWORD)

    def test_inactive_user_cannot_login(self, user):
        user.is_active = False
        user.save()
        with pytest.raises(AuthenticationError):
            login_with_password(email=user.email, password=PASSWORD)


@pytest.mark.django_db
class TestPostLoginRouting:
    def test_no_memberships_no_default_org(self, user):
        result = login_with_password(email=user.email, password=PASSWORD)
        assert result.default_org is None
        assert list(result.selectable_orgs) == []
        assert result.is_platform_user is False

    def test_single_active_membership_sets_default(self, user, org_a):
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE
        )
        result = login_with_password(email=user.email, password=PASSWORD)
        assert result.default_org == org_a
        assert list(result.selectable_orgs) == []

    def test_multiple_memberships_populate_selectable(self, user, org_a, org_b):
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE
        )
        Membership.objects.create(
            user=user, organization=org_b, status=Membership.Status.ACTIVE
        )
        result = login_with_password(email=user.email, password=PASSWORD)
        # Both orgs are selectable; no default unless one is flagged as such.
        assert result.default_org is None
        assert set(m.organization for m in result.selectable_orgs) == {org_a, org_b}

    def test_default_flag_sets_default_among_multiple(self, user, org_a, org_b):
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE, is_default=True
        )
        Membership.objects.create(
            user=user, organization=org_b, status=Membership.Status.ACTIVE
        )
        result = login_with_password(email=user.email, password=PASSWORD)
        assert result.default_org == org_a
        # Multi-org: picker is still shown so user can switch.
        assert len(result.selectable_orgs) == 2

    def test_inactive_membership_is_not_selectable(self, user, org_a):
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.SUSPENDED
        )
        result = login_with_password(email=user.email, password=PASSWORD)
        assert result.default_org is None
        assert list(result.selectable_orgs) == []

    def test_inactive_org_is_not_selectable(self, user, org_a):
        org_a.status = Organization.Status.INACTIVE
        org_a.save()
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE
        )
        result = login_with_password(email=user.email, password=PASSWORD)
        assert result.default_org is None
        assert list(result.selectable_orgs) == []

    def test_platform_user_flag_set_for_superuser(self, db):
        su = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
        result = login_with_password(email=su.email, password=PASSWORD)
        assert result.is_platform_user is True


@pytest.mark.django_db
class TestUserCanAccessOrg:
    def test_active_membership_grants_access(self, user, org_a):
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE
        )
        assert user_can_access_org(user=user, organization=org_a) is True

    def test_invited_membership_denies_access(self, user, org_a):
        # Only ACTIVE memberships grant access — INVITED / SUSPENDED / etc. do not.
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.INVITED
        )
        assert user_can_access_org(user=user, organization=org_a) is False

    def test_no_membership_denies_access(self, user, org_a):
        assert user_can_access_org(user=user, organization=org_a) is False

    def test_inactive_org_denies_access_even_with_active_membership(self, user, org_a):
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE
        )
        org_a.status = Organization.Status.INACTIVE
        org_a.save()
        assert user_can_access_org(user=user, organization=org_a) is False
