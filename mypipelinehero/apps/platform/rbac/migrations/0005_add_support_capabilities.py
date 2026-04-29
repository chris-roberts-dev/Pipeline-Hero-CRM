"""Add support.impersonation capabilities introduced in M2 step 5.

The original 0002_seed_capabilities migration is a no-op on existing
databases because Django won't re-run an already-applied migration. This
migration adds the new entries.

Idempotent: uses update_or_create keyed on `code`. Reverses by deleting
exactly the rows this migration adds — not the entire registry.
"""

from __future__ import annotations

from django.db import migrations


# Codes added in M2 step 5. Listed inline (not imported from the registry
# module) so this migration's behavior is locked in time — even if the
# registry is later edited, this migration only touches these specific rows.
NEW_CAPABILITIES = [
    {
        "code": "support.impersonation.start",
        "name": "Start a tenant impersonation session",
        "domain": "support",
        "description": (
            "High-trust action. Reason is mandatory. Sessions are time-boxed."
        ),
    },
    {
        "code": "support.impersonation.end_any",
        "name": "End any user's impersonation session",
        "domain": "support",
        "description": (
            "Self-end is always allowed; this covers ending another support "
            "user's session."
        ),
    },
]


def add_capabilities(apps, schema_editor):
    Capability = apps.get_model("rbac", "Capability")
    for spec in NEW_CAPABILITIES:
        Capability.objects.update_or_create(
            code=spec["code"],
            defaults={
                "name": spec["name"],
                "domain": spec["domain"],
                "description": spec["description"],
            },
        )


def remove_capabilities(apps, schema_editor):
    Capability = apps.get_model("rbac", "Capability")
    Capability.objects.filter(
        code__in=[spec["code"] for spec in NEW_CAPABILITIES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0004_membershipscopeassignment"),
    ]

    operations = [
        migrations.RunPython(add_capabilities, remove_capabilities),
    ]
