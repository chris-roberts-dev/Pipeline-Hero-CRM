"""Tests for role-assignment and scope-assignment services.

These services enforce the spec §7.2A line 735 invariant: scoped Manager
roles require a matching scope assignment. Tests cover both the happy
paths and the rejection paths.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.common.services import ValidationError
from apps.operations.locations.models import Market, Region
from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.models import (
    MembershipRole,
    MembershipScopeAssignment,
    Role,
)
from apps.platform.rbac.services import (
    add_scope_assignment,
    assign_role_to_membership,
    remove_role_from_membership,
    remove_scope_assignment,
    seed_default_roles_for_org,
)

User = get_user_model()


@pytest.fixture
def org(db):
    org = Organization.objects.create(name="Acme", slug="acme")
    seed_default_roles_for_org(org)
    return org


@pytest.fixture
def org_b(db):
    org = Organization.objects.create(name="Beta", slug="beta")
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
def region(db, org):
    return Region.objects.create(organization=org, name="East")


@pytest.fixture
def sales_role(db, org):
    return Role.objects.for_org(org).get(system_key=Role.SystemKey.SALES_STAFF)


@pytest.fixture
def regional_manager_role(db, org):
    return Role.objects.for_org(org).get(system_key=Role.SystemKey.REGIONAL_MANAGER)


# ---------------------------------------------------------------------------
# assign_role_to_membership
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssignRole:
    def test_unscoped_role_assigns_freely(self, membership, sales_role):
        a = assign_role_to_membership(membership=membership, role=sales_role)
        assert a.role == sales_role
        assert MembershipRole.objects.filter(
            membership=membership, role=sales_role
        ).exists()

    def test_idempotent(self, membership, sales_role):
        a1 = assign_role_to_membership(membership=membership, role=sales_role)
        a2 = assign_role_to_membership(membership=membership, role=sales_role)
        # Same row, no duplicates.
        assert a1.pk == a2.pk
        assert (
            MembershipRole.objects.filter(
                membership=membership, role=sales_role
            ).count()
            == 1
        )

    def test_scoped_role_without_scope_assignment_rejected(
        self, membership, regional_manager_role
    ):
        # No scope assignment exists yet — must be rejected.
        with pytest.raises(ValidationError, match="operating-scope assignment"):
            assign_role_to_membership(membership=membership, role=regional_manager_role)
        assert not MembershipRole.objects.filter(
            membership=membership, role=regional_manager_role
        ).exists()

    def test_scoped_role_with_scope_assignment_accepted(
        self, membership, regional_manager_role, region, org
    ):
        # Add the scope assignment FIRST.
        MembershipScopeAssignment.objects.create(
            organization=org, membership=membership, region=region
        )
        # Now the role can be assigned.
        a = assign_role_to_membership(membership=membership, role=regional_manager_role)
        assert a.role == regional_manager_role

    def test_cross_org_role_rejected(self, membership, org_b):
        # A role from org_b cannot be assigned to a membership in org.
        other_org_role = Role.objects.for_org(org_b).get(
            system_key=Role.SystemKey.SALES_STAFF
        )
        with pytest.raises(ValidationError, match="different organization"):
            assign_role_to_membership(membership=membership, role=other_org_role)


# ---------------------------------------------------------------------------
# remove_role_from_membership
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRemoveRole:
    def test_remove_existing(self, membership, sales_role):
        assign_role_to_membership(membership=membership, role=sales_role)
        assert remove_role_from_membership(membership=membership, role=sales_role)
        assert not MembershipRole.objects.filter(
            membership=membership, role=sales_role
        ).exists()

    def test_remove_nonexistent_returns_false(self, membership, sales_role):
        assert not remove_role_from_membership(membership=membership, role=sales_role)


# ---------------------------------------------------------------------------
# add_scope_assignment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAddScopeAssignment:
    def test_region_assignment(self, membership, region):
        a = add_scope_assignment(membership=membership, region=region)
        assert a.region == region
        assert a.kind == "region"

    def test_zero_targets_rejected(self, membership):
        with pytest.raises(ValidationError, match="Exactly one"):
            add_scope_assignment(membership=membership)

    def test_two_targets_rejected(self, membership, region, org):
        market = Market.objects.create(organization=org, region=region, name="Down")
        with pytest.raises(ValidationError, match="Exactly one"):
            add_scope_assignment(membership=membership, region=region, market=market)

    def test_cross_org_target_rejected(self, membership, org_b):
        # Region from another org cannot be assigned.
        other_region = Region.objects.create(organization=org_b, name="Other")
        with pytest.raises(ValidationError, match="same organization"):
            add_scope_assignment(membership=membership, region=other_region)


# ---------------------------------------------------------------------------
# remove_scope_assignment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRemoveScopeAssignment:
    def test_remove_when_no_scoped_role(self, membership, region):
        a = add_scope_assignment(membership=membership, region=region)
        remove_scope_assignment(assignment=a)
        assert not MembershipScopeAssignment.objects.filter(pk=a.pk).exists()

    def test_remove_last_when_scoped_role_active_rejected(
        self, membership, region, regional_manager_role, org
    ):
        # Set up: scope + scoped role.
        a = add_scope_assignment(membership=membership, region=region)
        assign_role_to_membership(membership=membership, role=regional_manager_role)
        # Removing the LAST scope assignment must be rejected to avoid
        # leaving the membership with a scoped role and no scope.
        with pytest.raises(ValidationError, match="last scope assignment"):
            remove_scope_assignment(assignment=a)
        # Assignment is still in place.
        assert MembershipScopeAssignment.objects.filter(pk=a.pk).exists()

    def test_remove_non_last_with_scoped_role_passes(
        self, membership, region, regional_manager_role, org
    ):
        # Two scope assignments + scoped role. Removing one leaves one.
        a1 = add_scope_assignment(membership=membership, region=region)
        west = Region.objects.create(organization=org, name="West")
        a2 = add_scope_assignment(membership=membership, region=west)
        assign_role_to_membership(membership=membership, role=regional_manager_role)

        # Removing a1 is fine — a2 remains.
        remove_scope_assignment(assignment=a1)
        assert not MembershipScopeAssignment.objects.filter(pk=a1.pk).exists()
        assert MembershipScopeAssignment.objects.filter(pk=a2.pk).exists()
