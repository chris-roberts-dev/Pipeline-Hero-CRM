"""Tests for the Region/Market/Location operating-scope models."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.operations.locations.models import Location, Market, Region
from apps.platform.organizations.models import Organization


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Alpha", slug="alpha")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Beta", slug="beta")


@pytest.fixture
def region(db, org_a):
    return Region.objects.create(organization=org_a, name="Eastern", code="E")


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
class TestRegion:
    def test_create(self, org_a):
        r = Region.objects.create(organization=org_a, name="Eastern")
        assert r.pk is not None

    def test_name_unique_within_org(self, org_a):
        Region.objects.create(organization=org_a, name="Eastern")
        with pytest.raises(IntegrityError):
            Region.objects.create(organization=org_a, name="Eastern")

    def test_same_name_allowed_across_orgs(self, org_a, org_b):
        Region.objects.create(organization=org_a, name="Eastern")
        Region.objects.create(organization=org_b, name="Eastern")
        assert Region.objects.filter(name="Eastern").count() == 2

    def test_code_unique_within_org_when_set(self, org_a):
        Region.objects.create(organization=org_a, name="R1", code="E")
        with pytest.raises(IntegrityError):
            Region.objects.create(organization=org_a, name="R2", code="E")

    def test_blank_codes_do_not_collide(self, org_a):
        # Partial constraint: blank codes are skipped.
        Region.objects.create(organization=org_a, name="R1", code="")
        Region.objects.create(organization=org_a, name="R2", code="")
        # Both should exist.
        assert Region.objects.filter(organization=org_a, code="").count() == 2

    def test_for_org_isolates(self, org_a, org_b):
        Region.objects.create(organization=org_a, name="A-Region")
        Region.objects.create(organization=org_b, name="B-Region")
        names = list(Region.objects.for_org(org_a).values_list("name", flat=True))
        assert names == ["A-Region"]

    def test_get_scope_location_returns_none(self, region):
        assert region.get_scope_location() is None


@pytest.mark.django_db
class TestMarket:
    def test_create(self, region):
        m = Market.objects.create(
            organization=region.organization, region=region, name="Downtown"
        )
        assert m.pk is not None

    def test_name_unique_within_region(self, region):
        Market.objects.create(
            organization=region.organization, region=region, name="Downtown"
        )
        with pytest.raises(IntegrityError):
            Market.objects.create(
                organization=region.organization, region=region, name="Downtown"
            )

    def test_same_name_allowed_in_different_regions(self, org_a):
        r1 = Region.objects.create(organization=org_a, name="East")
        r2 = Region.objects.create(organization=org_a, name="West")
        Market.objects.create(organization=org_a, region=r1, name="Downtown")
        Market.objects.create(organization=org_a, region=r2, name="Downtown")
        assert Market.objects.count() == 2

    def test_get_scope_location_returns_none(self, market):
        assert market.get_scope_location() is None


@pytest.mark.django_db
class TestLocation:
    def test_create(self, market):
        loc = Location.objects.create(
            organization=market.organization, market=market, name="Main"
        )
        assert loc.pk is not None

    def test_name_unique_within_market(self, market):
        Location.objects.create(
            organization=market.organization, market=market, name="Main"
        )
        with pytest.raises(IntegrityError):
            Location.objects.create(
                organization=market.organization, market=market, name="Main"
            )

    def test_get_scope_location_returns_self(self, location):
        # A Location IS its own scope-location. The evaluator uses this to
        # treat the leaf as both the target and the scope anchor.
        assert location.get_scope_location() == location

    def test_region_property_walks_up(self, location, region):
        assert location.region == region
