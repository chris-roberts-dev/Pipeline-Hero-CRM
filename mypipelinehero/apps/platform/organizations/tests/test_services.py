"""Tests for apps.platform.rbac.services.seed_default_roles_for_org."""

from __future__ import annotations

import pytest

from apps.platform.organizations.models import Organization
from apps.platform.rbac.capabilities import all_codes
from apps.platform.rbac.models import Capability, Role, RoleCapability
from apps.platform.rbac.role_templates import (
    SYSTEM_ROLE_TEMPLATES,
    resolve_capability_codes,
)
from apps.platform.rbac.services import seed_default_roles_for_org


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Beta", slug="beta")


@pytest.mark.django_db
class TestSeedDefaultRolesForOrg:

    def test_seeds_all_nine_roles(self, org):
        result = seed_default_roles_for_org(org)

        assert result.roles_created == 9
        assert result.roles_updated == 0
        assert Role.objects.for_org(org).count() == 9

    def test_all_seeded_roles_are_is_system(self, org):
        seed_default_roles_for_org(org)
        assert Role.objects.for_org(org).filter(is_system=True).count() == 9

    def test_all_system_keys_are_present(self, org):
        seed_default_roles_for_org(org)
        seeded_keys = set(
            Role.objects.for_org(org).values_list("system_key", flat=True)
        )
        expected = {t.system_key for t in SYSTEM_ROLE_TEMPLATES}
        assert seeded_keys == expected

    def test_owner_role_has_all_capabilities(self, org):
        seed_default_roles_for_org(org)
        owner = Role.objects.for_org(org).get(system_key=Role.SystemKey.OWNER)
        owner_codes = set(owner.capabilities.values_list("code", flat=True))
        assert owner_codes == set(all_codes())

    def test_viewer_role_has_only_view_capabilities(self, org):
        seed_default_roles_for_org(org)
        viewer = Role.objects.for_org(org).get(system_key=Role.SystemKey.VIEWER)
        viewer_codes = set(viewer.capabilities.values_list("code", flat=True))

        assert viewer_codes
        assert all(c.endswith(".view") for c in viewer_codes)
        # Cross-check against the resolver to catch drift.
        viewer_template = next(
            t for t in SYSTEM_ROLE_TEMPLATES if t.system_key == Role.SystemKey.VIEWER
        )
        assert viewer_codes == resolve_capability_codes(viewer_template)

    def test_sales_staff_has_expected_capabilities(self, org):
        seed_default_roles_for_org(org)
        sales = Role.objects.for_org(org).get(system_key=Role.SystemKey.SALES_STAFF)
        sales_codes = set(sales.capabilities.values_list("code", flat=True))

        # Core Sales Staff capabilities per spec §10.4
        must_have = {
            "leads.view",
            "leads.create",
            "leads.edit",
            "leads.convert",
            "quotes.view",
            "quotes.create",
            "quotes.send",
            "clients.view",
            "clients.create",
            "tasks.view",
            "tasks.create",
            "communications.view",
            "communications.log",
            "orders.view",
            "catalog.view",
        }
        assert must_have.issubset(sales_codes)

        # Capabilities Sales Staff should NOT have
        must_not_have = {
            "quotes.approve",
            "quotes.line.override_price",
            "billing.invoice.void",
            "admin.members.invite",
        }
        assert not sales_codes & must_not_have

    def test_is_idempotent_across_multiple_runs(self, org):
        # Running twice must not duplicate rows OR change capability counts.
        seed_default_roles_for_org(org)
        role_count_first = Role.objects.for_org(org).count()
        link_count_first = RoleCapability.objects.for_org(org).count()

        result = seed_default_roles_for_org(org)

        assert Role.objects.for_org(org).count() == role_count_first
        assert RoleCapability.objects.for_org(org).count() == link_count_first
        # Second run reports everything as "updated", nothing created.
        assert result.roles_created == 0
        assert result.roles_updated == 9

    def test_resync_adds_missing_links_without_duplicating(self, org):
        seed_default_roles_for_org(org)
        viewer = Role.objects.for_org(org).get(system_key=Role.SystemKey.VIEWER)

        # Manually delete one capability link from Viewer.
        removed_cap = Capability.objects.get(code="leads.view")
        RoleCapability.objects.filter(role=viewer, capability=removed_cap).delete()
        assert not viewer.capabilities.filter(code="leads.view").exists()

        result = seed_default_roles_for_org(org)

        # The missing link should be re-added; nothing else should change.
        assert viewer.capabilities.filter(code="leads.view").exists()
        assert result.capability_links_created == 1
        assert result.capability_links_removed == 0

    def test_resync_removes_stale_links(self, org):
        seed_default_roles_for_org(org)
        viewer = Role.objects.for_org(org).get(system_key=Role.SystemKey.VIEWER)

        # Artificially add a non-view capability that's NOT in the Viewer
        # template. A drift scenario — simulating a prior template change.
        stale_cap = Capability.objects.get(code="quotes.approve")
        RoleCapability.objects.create(
            organization=org, role=viewer, capability=stale_cap
        )
        assert viewer.capabilities.filter(code="quotes.approve").exists()

        result = seed_default_roles_for_org(org)

        assert not viewer.capabilities.filter(code="quotes.approve").exists()
        assert result.capability_links_removed == 1

    def test_seeding_is_isolated_between_orgs(self, org, org_b):
        seed_default_roles_for_org(org)
        seed_default_roles_for_org(org_b)

        assert Role.objects.for_org(org).count() == 9
        assert Role.objects.for_org(org_b).count() == 9
        # Total rows = 18 (no sharing of rows between orgs).
        assert Role.objects.count() == 18

    def test_tenant_custom_roles_are_not_touched(self, org):
        # Create a tenant-custom role (not seeded, no system_key). Seed the
        # defaults, then verify the custom role's capability set is untouched.
        custom = Role.objects.create(
            organization=org,
            name="Special Role",
            description="A tenant-defined role",
            is_system=False,
        )
        cap = Capability.objects.get(code="leads.view")
        RoleCapability.objects.create(organization=org, role=custom, capability=cap)

        seed_default_roles_for_org(org)

        assert custom.capabilities.filter(code="leads.view").exists()
        assert custom.capabilities.count() == 1
        # The seeding run shouldn't have converted it to a system role.
        custom.refresh_from_db()
        assert custom.is_system is False
        assert custom.system_key is None
