"""Unit tests for role_templates.py — pure, no DB."""

from __future__ import annotations

import pytest

from apps.platform.rbac.capabilities import all_codes
from apps.platform.rbac.models import Role
from apps.platform.rbac.role_templates import (
    ALL_CAPABILITIES,
    SYSTEM_ROLE_TEMPLATES,
    SystemRoleTemplate,
    resolve_capability_codes,
)


def test_nine_templates_exist():
    # Spec §10.4 defines exactly 9 system roles. Pin the count so a drop
    # or accidental addition shows up in code review.
    assert len(SYSTEM_ROLE_TEMPLATES) == 9


def test_every_systemkey_enum_has_a_template():
    # The import-time check in role_templates.py already guards this, but
    # testing it explicitly gives a clearer failure if someone removes the
    # check later.
    enum_keys = {choice.value for choice in Role.SystemKey}
    template_keys = {t.system_key for t in SYSTEM_ROLE_TEMPLATES}
    assert enum_keys == template_keys


def test_templates_are_frozen():
    t = SYSTEM_ROLE_TEMPLATES[0]
    with pytest.raises(Exception):
        t.name = "mutated"  # type: ignore[misc]


def test_sort_orders_are_unique():
    orders = [t.sort_order for t in SYSTEM_ROLE_TEMPLATES]
    assert len(orders) == len(set(orders)), (
        f"Sort orders must be unique for predictable UI ordering. Got: {orders}"
    )


def test_broad_roles_resolve_to_all_capabilities():
    # Owner, Org Admin, and the three Managers all use ALL_CAPABILITIES.
    broad_keys = {"OWNER", "ORG_ADMIN", "REGIONAL_MANAGER", "MARKET_MANAGER", "LOCATION_MANAGER"}
    for template in SYSTEM_ROLE_TEMPLATES:
        if template.system_key in broad_keys:
            resolved = resolve_capability_codes(template)
            assert resolved == set(all_codes()), (
                f"Expected {template.system_key} to resolve to all capabilities; "
                f"missing: {set(all_codes()) - resolved}"
            )


def test_viewer_resolves_to_only_view_capabilities():
    viewer = next(t for t in SYSTEM_ROLE_TEMPLATES if t.system_key == Role.SystemKey.VIEWER)
    resolved = resolve_capability_codes(viewer)
    # Every resolved code must end in .view...
    non_view = [c for c in resolved if not c.endswith(".view")]
    assert not non_view, f"Viewer has non-view capabilities: {non_view}"
    # ...and every .view code in the registry must be in the set.
    expected = {c for c in all_codes() if c.endswith(".view")}
    assert resolved == expected


def test_sales_staff_has_expected_capabilities():
    sales = next(t for t in SYSTEM_ROLE_TEMPLATES if t.system_key == Role.SystemKey.SALES_STAFF)
    resolved = resolve_capability_codes(sales)

    # Spot checks per the spec: Sales Staff gets leads.*
    assert "leads.view" in resolved
    assert "leads.convert" in resolved

    # ...but NOT quotes.approve (that's the highest-trust quote action).
    assert "quotes.approve" not in resolved
    # ...and NOT billing capabilities.
    assert not any(c.startswith("billing.") for c in resolved)
    # ...and NOT admin capabilities.
    assert not any(c.startswith("admin.") for c in resolved)


def test_service_staff_is_narrow():
    service = next(t for t in SYSTEM_ROLE_TEMPLATES if t.system_key == Role.SystemKey.SERVICE_STAFF)
    resolved = resolve_capability_codes(service)
    assert resolved == {
        "workorders.view",
        "workorders.update_status",
        "workorders.complete",
        "tasks.view",
        "tasks.complete",
    }


def test_production_staff_is_narrow():
    production = next(
        t for t in SYSTEM_ROLE_TEMPLATES if t.system_key == Role.SystemKey.PRODUCTION_STAFF
    )
    resolved = resolve_capability_codes(production)
    assert resolved == {
        "build.view",
        "build.manage",
        "build.labor.record",
        "tasks.view",
        "tasks.complete",
    }


def test_template_with_unknown_capability_raises():
    # Defensive check against typos. Build a template with a nonsense
    # capability code and confirm resolution rejects it.
    bogus = SystemRoleTemplate(
        system_key="NOT_A_REAL_KEY",
        name="Bogus",
        description="",
        capabilities={"leads.view", "does.not.exist"},
    )
    with pytest.raises(ValueError, match="unknown capabilities"):
        resolve_capability_codes(bogus)


def test_all_capabilities_marker_is_a_singleton():
    # Multiple imports shouldn't create distinct instances.
    from apps.platform.rbac.role_templates import ALL_CAPABILITIES as imported_again
    assert imported_again is ALL_CAPABILITIES
