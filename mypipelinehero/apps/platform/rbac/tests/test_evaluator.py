"""Tests for the permission evaluator (apps.platform.rbac.evaluator)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.evaluator import (
    get_acting_membership,
    has_capability,
    object_check,
)
from apps.platform.rbac.models import (
    Capability,
    MembershipCapabilityGrant,
    MembershipRole,
    Role,
    RoleCapability,
)
from apps.platform.rbac.services import seed_default_roles_for_org

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def sales_role(db, org):
    return Role.objects.for_org(org).get(system_key=Role.SystemKey.SALES_STAFF)


@pytest.fixture
def viewer_role(db, org):
    return Role.objects.for_org(org).get(system_key=Role.SystemKey.VIEWER)


@pytest.fixture
def owner_role(db, org):
    return Role.objects.for_org(org).get(system_key=Role.SystemKey.OWNER)


@pytest.fixture
def request_factory():
    return RequestFactory()


# ---------------------------------------------------------------------------
# Step 1: superuser short-circuit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSuperuserShortCircuit:
    def test_superuser_grants_any_capability(self, db):
        admin = User.objects.create_superuser(email="root@example.com", password="x" * 12)
        # No membership at all — superuser bypass means it doesn't matter.
        assert has_capability(
            user=admin, membership=None, capability_code="quotes.approve"
        )

    def test_superuser_grants_in_object_check_too(self, db, org):
        admin = User.objects.create_superuser(email="root@example.com", password="x" * 12)
        # Cross-tenant target. Superuser still grants — superuser is
        # platform-level, not bound by org tenancy at the cap layer.
        # (Platform-level audit and access logging is a separate concern.)
        target = type("FakeTarget", (), {"organization_id": org.pk})()
        assert object_check(
            user=admin, membership=None, capability_code="leads.view", target=target
        )


# ---------------------------------------------------------------------------
# Step 3: membership presence and status checks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMembershipPresence:
    def test_no_membership_denies(self, user):
        assert not has_capability(
            user=user, membership=None, capability_code="leads.view"
        )

    def test_inactive_membership_denies(self, user, org):
        suspended = Membership.objects.create(
            user=user, organization=org, status=Membership.Status.SUSPENDED
        )
        # Even with the role assigned, suspended membership can't act.
        owner_role = Role.objects.for_org(org).get(system_key=Role.SystemKey.OWNER)
        MembershipRole.objects.create(
            organization=org, membership=suspended, role=owner_role
        )
        assert not has_capability(
            user=user, membership=suspended, capability_code="leads.view"
        )

    def test_invited_membership_denies(self, user, org):
        # INVITED is the pre-acceptance state. Should not yet hold capabilities.
        invited = Membership.objects.create(
            user=user, organization=org, status=Membership.Status.INVITED
        )
        owner_role = Role.objects.for_org(org).get(system_key=Role.SystemKey.OWNER)
        MembershipRole.objects.create(
            organization=org, membership=invited, role=owner_role
        )
        assert not has_capability(
            user=user, membership=invited, capability_code="leads.view"
        )


# ---------------------------------------------------------------------------
# Step 4: role-derived capabilities
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRoleDerivedCapabilities:
    def test_membership_with_no_roles_has_no_capabilities(self, user, membership):
        assert not has_capability(
            user=user, membership=membership, capability_code="leads.view"
        )

    def test_owner_role_grants_every_capability(
        self, user, membership, owner_role, org
    ):
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        # Spot-check across domains.
        assert has_capability(user=user, membership=membership, capability_code="leads.view")
        assert has_capability(user=user, membership=membership, capability_code="quotes.approve")
        assert has_capability(user=user, membership=membership, capability_code="billing.invoice.void")
        assert has_capability(user=user, membership=membership, capability_code="admin.members.invite")

    def test_viewer_role_grants_only_view_capabilities(
        self, user, membership, viewer_role, org
    ):
        MembershipRole.objects.create(
            organization=org, membership=membership, role=viewer_role
        )
        assert has_capability(user=user, membership=membership, capability_code="leads.view")
        assert has_capability(user=user, membership=membership, capability_code="quotes.view")
        # ...but not mutating ones.
        assert not has_capability(
            user=user, membership=membership, capability_code="leads.create"
        )
        assert not has_capability(
            user=user, membership=membership, capability_code="quotes.approve"
        )

    def test_multiple_roles_capabilities_are_unioned(
        self, user, membership, sales_role, org
    ):
        # Sales gives leads.create; Viewer gives leads.view.
        viewer = Role.objects.for_org(org).get(system_key=Role.SystemKey.VIEWER)
        MembershipRole.objects.create(
            organization=org, membership=membership, role=sales_role
        )
        MembershipRole.objects.create(
            organization=org, membership=membership, role=viewer
        )
        # Both sets are visible.
        assert has_capability(
            user=user, membership=membership, capability_code="leads.create"
        )
        # Quotes.view is in viewer but not in sales — proves union, not intersection.
        assert has_capability(
            user=user, membership=membership, capability_code="quotes.view"
        )


# ---------------------------------------------------------------------------
# Step 5: GRANT and DENY overrides
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGrantOverrides:
    def test_grant_adds_capability_beyond_role_set(
        self, user, membership, viewer_role, org
    ):
        # Viewer has no quotes.approve. Add it via per-membership GRANT.
        MembershipRole.objects.create(
            organization=org, membership=membership, role=viewer_role
        )
        cap = Capability.objects.get(code="quotes.approve")
        MembershipCapabilityGrant.objects.create(
            organization=org,
            membership=membership,
            capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
        )
        assert has_capability(
            user=user, membership=membership, capability_code="quotes.approve"
        )

    def test_deny_removes_capability_from_role_set(
        self, user, membership, owner_role, org
    ):
        # Owner has everything. Add a DENY on billing.invoice.void.
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        cap = Capability.objects.get(code="billing.invoice.void")
        MembershipCapabilityGrant.objects.create(
            organization=org,
            membership=membership,
            capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.DENY,
        )
        assert not has_capability(
            user=user, membership=membership, capability_code="billing.invoice.void"
        )
        # Other Owner capabilities still work.
        assert has_capability(
            user=user, membership=membership, capability_code="leads.view"
        )

    def test_deny_takes_precedence_over_grant(
        self, user, membership, viewer_role, org
    ):
        # Spec §10.2 step 5: DENY beats GRANT for the same capability.
        MembershipRole.objects.create(
            organization=org, membership=membership, role=viewer_role
        )
        cap = Capability.objects.get(code="quotes.approve")
        # Both GRANT and DENY for the same cap.
        MembershipCapabilityGrant.objects.create(
            organization=org, membership=membership, capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.GRANT,
        )
        MembershipCapabilityGrant.objects.create(
            organization=org, membership=membership, capability=cap,
            grant_type=MembershipCapabilityGrant.GrantType.DENY,
        )
        assert not has_capability(
            user=user, membership=membership, capability_code="quotes.approve"
        )


# ---------------------------------------------------------------------------
# Step 7: object-level tenancy check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestObjectTenancyCheck:
    def test_target_in_same_org_passes(
        self, user, membership, owner_role, org
    ):
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        target = type("FakeTarget", (), {"organization_id": org.pk})()
        assert object_check(
            user=user, membership=membership, capability_code="leads.edit", target=target
        )

    def test_target_in_different_org_fails(
        self, user, membership, owner_role, org, org_b
    ):
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        # Target belongs to a DIFFERENT org. Even with full Owner caps in
        # `org`, the object-level tenancy check must deny.
        target = type("FakeTarget", (), {"organization_id": org_b.pk})()
        assert not object_check(
            user=user, membership=membership, capability_code="leads.edit", target=target
        )

    def test_target_without_organization_attribute_skips_tenancy_check(
        self, user, membership, owner_role, org
    ):
        # Some objects (rare) are inherently global. Tenancy check is
        # skipped if `organization_id` isn't present. The cap check still
        # runs, so this isn't a bypass — just an opt-out for global rows.
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        target = type("GlobalTarget", (), {})()  # no organization attr
        assert object_check(
            user=user, membership=membership, capability_code="leads.view", target=target
        )


# ---------------------------------------------------------------------------
# Per-request caching
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPerRequestCache:
    def test_request_cache_avoids_repeated_queries(
        self, user, membership, owner_role, org, request_factory, django_assert_num_queries
    ):
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        request = request_factory.get("/")

        # First call hits the DB (2 queries: role caps + grants).
        with django_assert_num_queries(2):
            assert has_capability(
                user=user, membership=membership,
                capability_code="leads.view", request=request,
            )

        # Second call (same cap) is cached: 0 DB queries.
        with django_assert_num_queries(0):
            assert has_capability(
                user=user, membership=membership,
                capability_code="leads.view", request=request,
            )

        # Different cap on the same request: still hits DB (different cache key).
        with django_assert_num_queries(2):
            assert has_capability(
                user=user, membership=membership,
                capability_code="quotes.view", request=request,
            )

    def test_no_request_means_no_cache(
        self, user, membership, owner_role, org, django_assert_num_queries
    ):
        MembershipRole.objects.create(
            organization=org, membership=membership, role=owner_role
        )
        # Without a request, every call hits the DB.
        with django_assert_num_queries(2):
            has_capability(user=user, membership=membership, capability_code="leads.view")
        with django_assert_num_queries(2):
            has_capability(user=user, membership=membership, capability_code="leads.view")


# ---------------------------------------------------------------------------
# get_acting_membership helper
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetActingMembership:
    def test_returns_active_membership(self, user, membership, org):
        assert get_acting_membership(user=user, organization=org) == membership

    def test_returns_none_for_unauthenticated_user(self, org):
        from django.contrib.auth.models import AnonymousUser
        assert get_acting_membership(user=AnonymousUser(), organization=org) is None

    def test_returns_none_when_no_organization(self, user):
        assert get_acting_membership(user=user, organization=None) is None

    def test_returns_none_for_inactive_membership(self, user, org):
        Membership.objects.create(
            user=user, organization=org, status=Membership.Status.SUSPENDED
        )
        assert get_acting_membership(user=user, organization=org) is None
