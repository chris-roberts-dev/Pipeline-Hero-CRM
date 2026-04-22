"""Tests for Organization, Membership, and the TenantManager.for_org helper."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.platform.organizations.models import Membership, Organization

User = get_user_model()


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOrganization:
    def test_create_with_valid_slug(self) -> None:
        org = Organization.objects.create(name="Acme Co", slug="acme")
        assert org.status == Organization.Status.ACTIVE
        assert org.is_active is True
        assert str(org) == "Acme Co (acme)"

    def test_slug_unique(self) -> None:
        Organization.objects.create(name="Acme", slug="acme")
        with pytest.raises(IntegrityError):
            Organization.objects.create(name="Acme Other", slug="acme")

    @pytest.mark.parametrize(
        "bad_slug",
        [
            "ACME",          # uppercase
            "-acme",         # leading hyphen
            "acme-",         # trailing hyphen
            "ac me",         # space
            "acme.co",       # dot
            "ac_me",         # underscore
        ],
    )
    def test_slug_validator_rejects_invalid(self, bad_slug: str) -> None:
        org = Organization(name="X", slug=bad_slug)
        with pytest.raises(ValidationError):
            org.full_clean()

    def test_inactive_org_reports_is_active_false(self) -> None:
        org = Organization.objects.create(
            name="X", slug="x", status=Organization.Status.INACTIVE
        )
        assert org.is_active is False


# ---------------------------------------------------------------------------
# Membership + tenant manager
# ---------------------------------------------------------------------------


@pytest.fixture
def two_orgs(db) -> tuple[Organization, Organization]:
    a = Organization.objects.create(name="Alpha", slug="alpha")
    b = Organization.objects.create(name="Beta", slug="beta")
    return a, b


@pytest.fixture
def user(db) -> "User":
    return User.objects.create_user(email="user@example.com", password="x" * 12)


@pytest.mark.django_db
class TestMembership:
    def test_create_membership_defaults_to_invited(self, user, two_orgs) -> None:
        a, _ = two_orgs
        m = Membership.objects.create(user=user, organization=a)
        assert m.status == Membership.Status.INVITED
        assert m.is_default is False

    def test_user_org_pair_is_unique(self, user, two_orgs) -> None:
        a, _ = two_orgs
        Membership.objects.create(user=user, organization=a)
        with pytest.raises(IntegrityError):
            Membership.objects.create(user=user, organization=a)

    def test_user_may_belong_to_multiple_orgs(self, user, two_orgs) -> None:
        a, b = two_orgs
        Membership.objects.create(user=user, organization=a)
        Membership.objects.create(user=user, organization=b)
        assert Membership.objects.filter(user=user).count() == 2

    def test_only_one_default_membership_per_user(self, user, two_orgs) -> None:
        a, b = two_orgs
        Membership.objects.create(user=user, organization=a, is_default=True)
        with pytest.raises(IntegrityError):
            Membership.objects.create(user=user, organization=b, is_default=True)

    def test_non_default_memberships_are_unconstrained(self, user, two_orgs) -> None:
        # Two memberships, neither default — must succeed.
        a, b = two_orgs
        Membership.objects.create(user=user, organization=a, is_default=False)
        Membership.objects.create(user=user, organization=b, is_default=False)
        assert Membership.objects.filter(user=user, is_default=False).count() == 2


# ---------------------------------------------------------------------------
# TenantManager.for_org — the thing that prevents cross-tenant leakage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantManagerForOrg:
    def test_for_org_filters_to_single_org(self, user, two_orgs) -> None:
        a, b = two_orgs
        # Need a second user because the user<->org pair is unique.
        other = User.objects.create_user(email="other@example.com", password="x" * 12)
        m_a = Membership.objects.create(user=user, organization=a)
        Membership.objects.create(user=other, organization=b)

        in_a = list(Membership.objects.for_org(a))
        assert in_a == [m_a]

    def test_for_org_accepts_pk_not_just_instance(self, user, two_orgs) -> None:
        a, _ = two_orgs
        Membership.objects.create(user=user, organization=a)
        assert Membership.objects.for_org(a.pk).count() == 1

    def test_for_org_is_chainable_with_filter(self, user, two_orgs) -> None:
        a, _ = two_orgs
        m = Membership.objects.create(user=user, organization=a, status=Membership.Status.ACTIVE)
        qs = Membership.objects.for_org(a).filter(status=Membership.Status.ACTIVE)
        assert list(qs) == [m]
