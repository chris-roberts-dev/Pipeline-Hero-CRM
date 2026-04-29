"""Unit tests for the capability registry module.

These are pure-Python tests — no DB, no fixtures. They verify that the
registry itself is internally consistent. DB-level seeding is tested
separately in test_models.py (which relies on the migration having run).
"""

from __future__ import annotations

import re

import pytest

from apps.platform.rbac.capabilities import (
    CAPABILITIES,
    all_codes,
    by_domain,
)

# Pattern from spec §10.3: codes follow `{domain}.{resource}.{action}`
# but note some entries in the spec only have two segments (e.g.
# `leads.view`, `quotes.edit`) — "domain.action" without an explicit
# resource. Others have four (e.g. `quotes.line.override_price`). So the
# pattern is really: two or more dot-separated lowercase-alphanumeric-
# underscore segments.
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}$")


def test_registry_is_non_empty():
    assert len(CAPABILITIES) > 0


def test_expected_capability_count():
    # Pinning the count so accidental drops or additions surface in code
    # review. If you legitimately add/remove capabilities, update this
    # number in the same commit.
    assert len(CAPABILITIES) == 86


def test_all_codes_match_pattern():
    bad = [c.code for c in CAPABILITIES if not _CODE_PATTERN.match(c.code)]
    assert not bad, f"Capability codes violating naming pattern: {bad}"


def test_no_duplicate_codes():
    codes = all_codes()
    assert len(codes) == len(set(codes))


def test_domain_matches_code_prefix():
    # The `domain` field is derived from the first segment of the code.
    # Mismatch would confuse the admin UI grouping, so enforce it here.
    for spec in CAPABILITIES:
        expected = spec.code.split(".", 1)[0]
        assert spec.domain == expected, (
            f"Capability {spec.code!r} has domain={spec.domain!r}, "
            f"expected {expected!r}"
        )


def test_every_capability_has_a_name():
    for spec in CAPABILITIES:
        assert spec.name, f"Capability {spec.code!r} has no display name"


def test_capabilityspec_is_frozen():
    # Defensive: the dataclass is frozen so the registry can't be
    # accidentally mutated at runtime.
    spec = CAPABILITIES[0]
    with pytest.raises(Exception):
        spec.name = "mutated"  # type: ignore[misc]


def test_by_domain_groups_all_entries():
    groups = by_domain()
    total = sum(len(specs) for specs in groups.values())
    assert total == len(CAPABILITIES)


def test_expected_domains_present():
    # Sanity check: we have all 14 expected domains. Originally 13 from
    # spec §10.3 plus 'support' added in M2 step 5 for cross-tenant
    # platform-staff capabilities (impersonation, etc.) — these aren't
    # tenant-business domains but live in the same registry.
    expected_domains = {
        "leads",
        "quotes",
        "clients",
        "orders",
        "catalog",
        "workorders",
        "purchasing",
        "build",
        "billing",
        "tasks",
        "communications",
        "reporting",
        "admin",
        "support",
    }
    assert set(by_domain().keys()) == expected_domains


def test_highest_trust_codes_are_present():
    # Spot-check a few capabilities that would be embarrassing to miss.
    codes = set(all_codes())
    must_exist = {
        "quotes.approve",  # quote acceptance — spec §10.3 "highest-trust"
        "quotes.line.override_price",
        "billing.invoice.void",
        "billing.payment.edit",
        "admin.capabilities.grant",
        "build.qa.review",
    }
    missing = must_exist - codes
    assert not missing, f"Critical capabilities missing from registry: {missing}"
