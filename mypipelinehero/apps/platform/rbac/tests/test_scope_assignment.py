"""Tests for MembershipScopeAssignment — the three-FK + CHECK pattern."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.operations.locations.models import Location, Market, Region
from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.models import MembershipScopeAssignment

User = get_user_model()


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


@pytest.fixture
def region(db, org):
    return Region.objects.create(organization=org, name="Eastern")


@pytest.fixture
def market(db, region):
    return Market.objects.create(
        organization=region.organization, region=region, name="Downtown"
    )


@pytest.fixture
def location(db, market):
    return Location.objects.create(
        organization=market.organization, market=market, name="Main Office"
    )


@pytest.mark.django_db
class TestExactlyOneTargetConstraint:
    def test_region_only_passes(self, org, membership, region):
        a = MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, region=region
        )
        assert a.kind == "region"
        assert a.target == region

    def test_market_only_passes(self, org, membership, market):
        a = MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, market=market
        )
        assert a.kind == "market"
        assert a.target == market

    def test_location_only_passes(self, org, membership, location):
        a = MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, location=location
        )
        assert a.kind == "location"
        assert a.target == location

    def test_zero_targets_fails(self, org, membership):
        # All three null violates the CHECK constraint.
        with pytest.raises(IntegrityError), transaction.atomic():
            MembershipScopeAssignment.objects.create(
                organization=org, membership=membership
            )

    def test_two_targets_fails(self, org, membership, region, market):
        with pytest.raises(IntegrityError), transaction.atomic():
            MembershipScopeAssignment.objects.create(
                organization=org,
                membership=membership,
                region=region,
                market=market,
            )

    def test_three_targets_fails(self, org, membership, region, market, location):
        with pytest.raises(IntegrityError), transaction.atomic():
            MembershipScopeAssignment.objects.create(
                organization=org,
                membership=membership,
                region=region,
                market=market,
                location=location,
            )


@pytest.mark.django_db
class TestNoDuplicateAssignmentsConstraint:
    def test_duplicate_region_blocked(self, org, membership, region):
        MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, region=region
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            MembershipScopeAssignment.objects.create(
                organization=org, membership=membership, region=region
            )

    def test_different_regions_allowed(self, org, membership):
        r1 = Region.objects.create(organization=org, name="East")
        r2 = Region.objects.create(organization=org, name="West")
        MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, region=r1
        )
        MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, region=r2
        )
        assert membership.scope_assignments.count() == 2


@pytest.mark.django_db
class TestForOrgIsolation:
    def test_for_org_filters_correctly(self, db):
        org_a = Organization.objects.create(name="A", slug="a")
        org_b = Organization.objects.create(name="B", slug="b")
        u = User.objects.create_user(email="u@example.com", password="x" * 12)
        m_a = Membership.objects.create(
            user=u, organization=org_a, status=Membership.Status.ACTIVE
        )
        m_b = Membership.objects.create(
            user=u, organization=org_b, status=Membership.Status.ACTIVE
        )
        r_a = Region.objects.create(organization=org_a, name="EastA")
        r_b = Region.objects.create(organization=org_b, name="EastB")
        MembershipScopeAssignment.objects.create(
            organization=org_a, membership=m_a, region=r_a
        )
        MembershipScopeAssignment.objects.create(
            organization=org_b, membership=m_b, region=r_b
        )

        scoped_a = MembershipScopeAssignment.objects.for_org(org_a)
        assert scoped_a.count() == 1
        assert scoped_a.first().membership == m_a
