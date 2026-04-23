"""Seed the Capability table with the platform's system-defined codes.

Reads from apps.platform.rbac.capabilities. That module is also imported at
runtime for the permission evaluator and role seeding, so keeping the list
in one place means "the registry" is a single source of truth.

Idempotent: uses update_or_create keyed on `code`, so running this migration
on a DB that already has some capabilities doesn't produce duplicates and
DOES update name/domain/description if they've changed.

Why not hard-code the list inline?
  Best-practice guidance is to inline data migration contents so they don't
  break when the source module changes later. We accept that risk here
  because:
    (a) Capability codes are an append-only, never-rename contract. The
        registry is structured to make the "add new, never rename" rule
        obvious.
    (b) Writing the full list twice (once in code, once in this migration)
        would guarantee drift.
    (c) If this module's import ever breaks, future Django migrations will
        fail loudly at `migrate` time, which is fine — we'd fix the import.
"""

from __future__ import annotations

from django.db import migrations


def seed_capabilities(apps, schema_editor):
    Capability = apps.get_model("rbac", "Capability")

    # Imported inside the function so makemigrations' autodetector doesn't
    # run this import at migration-loading time.
    from apps.platform.rbac.capabilities import CAPABILITIES

    for spec in CAPABILITIES:
        Capability.objects.update_or_create(
            code=spec.code,
            defaults={
                "name": spec.name,
                "domain": spec.domain,
                "description": spec.description,
            },
        )


def unseed_capabilities(apps, schema_editor):
    """Reverse operation: remove the seeded rows.

    Cascade is PROTECT on RoleCapability and MembershipCapabilityGrant, so
    this will correctly fail if any capability is in use — which is the
    right behavior. If you really need to roll back, remove the
    dependent rows first.
    """
    Capability = apps.get_model("rbac", "Capability")

    from apps.platform.rbac.capabilities import all_codes

    Capability.objects.filter(code__in=all_codes()).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("rbac", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_capabilities, unseed_capabilities),
    ]
