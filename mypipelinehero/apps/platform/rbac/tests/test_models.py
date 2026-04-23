"""Tests for the RBAC model layer.

Covers:
  - the data migration actually populated the Capability table
  - model constraints (role-name uniqueness per org, system-key uniqueness, etc.)
  - MembershipCapabilityGrant grant/deny semantics at the row level
  - TenantManager.for_org still works on all three tenant models

The permission evaluator is tested separately when it lands in the next
step — these tests focus on data layer integrity.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.capabilities import CAPABILITIES, all_codes
from apps.platform.rbac.models import (
    Capability,
    MembershipCapabilityGrant,
    Role,
    RoleCapability,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Data migration verification
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCapabilitySeedMigration:
    """The 0002_seed_capabilities data migration runs on test DB setup,
    so every capability from the registry must be present before any
    individual test runs."""

    def test_every_registry_code_is_in_db(self):
        db_codes = set(Capability.objects.values_list("code", flat=True))
        missing = set(all_codes()) - db_codes
        assert not missing, f"Capabilities missing from DB after migration: {missing}"

    def test_db_row_count_matches_registry(self):
        # Strict equality: extra rows are as much a bug as missing ones.
        # If this fails, something seeded capabilities outside the migration.
        assert Capability.objects.count() == len(CAPABILITIES)

    def test_seeded_fields_match_registry(self):
        # Spot-check that the name / domain / description round-tripped
        # correctly. Full equality on all 84 rows would be excessive.
        sample = Capability.objects.get(code="quotes.approve")
        spec = next(c for c in CAPABILITIES if c.code == "quotes.approve")
        assert sample.name == spec.name
        assert sample.domain == spec.domain
        assert sample.description == spec.description


# ---------------------------------------------------------------------------
# Role model
# ---------------------------------------------------------------------------


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Alpha", slug="alpha")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Beta", slug="beta")


@pytest.mark.django_db
class TestRole:
    def test_role_name_unique_within_org(self, org_a):
        Role.objects.create(organization=org_a, name="Sales Staff")
        with pytest.raises(IntegrityError):
            Role.objects.create(organization=org_a, name="Sales Staff")

    def test_same_role_name_allowed_across_orgs(self, org_a, org_b):
        # Each org owns its own "Sales Staff" role — that's the whole point
        # of per-org role seeding per §10.4.
        Role.objects.create(organization=org_a, name="Sales Staff")
        Role.objects.create(organization=org_b, name="Sales Staff")
        assert Role.objects.filter(name="Sales Staff").count() == 2

    def test_system_key_unique_within_org(self, org_a):
        Role.objects.create(
            organization=org_a,
            name="Sales Staff",
            is_system=True,
            system_key=Role.SystemKey.SALES_STAFF,
        )
        with pytest.raises(IntegrityError):
            # Second Sales Staff template for the same org — forbidden.
            Role.objects.create(
                organization=org_a,
                name="Sales Staff 2",  # different name, same system_key
                is_system=True,
                system_key=Role.SystemKey.SALES_STAFF,
            )

    def test_null_system_key_is_not_constrained(self, org_a):
        # Tenant-custom roles have system_key=NULL. Multiple custom roles
        # with NULL system_key must coexist peacefully.
        Role.objects.create(organization=org_a, name="Custom One")
        Role.objects.create(organization=org_a, name="Custom Two")
        assert Role.objects.filter(organization=org_a, system_key__isnull=True).count() == 2

    def test_for_org_isolates_roles(self, org_a, org_b):
        Role.objects.create(organization=org_a, name="A Role")
        Role.objects.create(organization=org_b, name="B Role")
        in_a = list(Role.objects.for_org(org_a).values_list("name", flat=True))
        assert in_a == ["A Role"]


# ---------------------------------------------------------------------------
# RoleCapability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRoleCapability:
    def test_link_capability_to_role(self, org_a):
        role = Role.objects.create(organization=org_a, name="Sales")
        cap = Capability.objects.get(code="leads.view")
        RoleCapability.objects.create(organization=org_a, role=role, capability=cap)

        assert list(role.capabilities.values_list("code", flat=True)) == ["leads.view"]

    def test_same_capability_cannot_be_added_twice_to_a_role(self, org_a):
        role = Role.objects.create(organization=org_a, name="Sales")
        cap = Capability.objects.get(code="leads.view")
        RoleCapability.objects.create(organization=org_a, role=role, capability=cap)
        with pytest.raises(IntegrityError):
            RoleCapability.objects.create(organization=org_a, role=role, capability=cap)

    def test_same_capability_on_different_roles_is_allowed(self, org_a):
        r1 = Role.objects.create(organization=org_a, name="R1")
        r2 = Role.objects.create(organization=org_a, name="R2")
        cap = Capability.objects.get(code="leads.view")
        RoleCapability.objects.create(organization=org_a, role=r1, capability=cap)
        RoleCapability.objects.create(organization=org_a, role=r2, capability=cap)
        assert RoleCapability.objects.filter(capability=cap).count() == 2


# ---------------------------------------------------------------------------
# MembershipCapabilityGrant
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(email="u@example.com", password="x" * 12)


@pytest.fixture
def membership_a(db, user, org_a):
    return Membership.objects.create(
        user=user, organization=org_a, status=Membership.Status.ACTIVE
    )


@pytest.mark.django_db
class TestMembershipCapabilityGrant:
    def test_create_grant(self, org_a, membership_a):
        cap = Capability.objects.get(code="quotes.approve")
        MembershipCapabilityGrant.objects.create(
            organization=org_a,
            membership=membership_a,
            capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
            reason="Temporary project approval rights",
        )
        assert membership_a.capability_grants.count() == 1

    def test_duplicate_same_type_is_blocked(self, org_a, membership_a):
        cap = Capability.objects.get(code="quotes.approve")
        MembershipCapabilityGrant.objects.create(
            organization=org_a,
            membership=membership_a,
            capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
        )
        with pytest.raises(IntegrityError):
            MembershipCapabilityGrant.objects.create(
                organization=org_a,
                membership=membership_a,
                capability=cap,
                grant_type=MembershipCapabilityGrant.GrantType.GRANT,
            )

    def test_both_grant_and_deny_for_same_cap_can_coexist(self, org_a, membership_a):
        # Unusual but not forbidden — the evaluator resolves this by
        # applying DENY precedence. The data layer allows the rows so an
        # admin could inspect both.
        cap = Capability.objects.get(code="quotes.approve")
        MembershipCapabilityGrant.objects.create(
            organization=org_a,
            membership=membership_a,
            capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
        )
        MembershipCapabilityGrant.objects.create(
            organization=org_a,
            membership=membership_a,
            capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.DENY,
        )
        assert membership_a.capability_grants.count() == 2

    def test_for_org_isolates_grants(self, org_a, org_b, user):
        # Create membership in each org, attach a grant to each, verify
        # queryset scoping still works end-to-end.
        mem_a = Membership.objects.get(user=user, organization=org_a)
        mem_b = Membership.objects.create(
            user=user, organization=org_b, status=Membership.Status.ACTIVE
        )
        cap = Capability.objects.get(code="leads.view")
        MembershipCapabilityGrant.objects.create(
            organization=org_a, membership=mem_a, capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
        )
        MembershipCapabilityGrant.objects.create(
            organization=org_b, membership=mem_b, capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
        )

        in_a = MembershipCapabilityGrant.objects.for_org(org_a)
        assert in_a.count() == 1
        assert in_a.first().membership == mem_a
