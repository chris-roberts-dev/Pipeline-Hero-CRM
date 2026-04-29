"""Add MembershipScopeAssignment.

Per spec §7.2A: a Membership may have one or more scope assignments. Each
assignment scopes the membership to a Region, Market, or Location —
exactly one of the three (DB-enforced via CHECK constraint).

Hand-written rather than auto-generated to keep this step's ship
self-contained.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("rbac", "0003_membershiprole"),
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MembershipScopeAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reason", models.CharField(blank=True, max_length=255)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scope_assignments",
                        to="organizations.membership",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scope_assignments",
                        to="locations.region",
                    ),
                ),
                (
                    "market",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scope_assignments",
                        to="locations.market",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scope_assignments",
                        to="locations.location",
                    ),
                ),
            ],
            options={
                "verbose_name": "membership scope assignment",
                "verbose_name_plural": "membership scope assignments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="membershipscopeassignment",
            constraint=models.CheckConstraint(
                condition=(
                    (
                        models.Q(region__isnull=False)
                        & models.Q(market__isnull=True)
                        & models.Q(location__isnull=True)
                    )
                    | (
                        models.Q(region__isnull=True)
                        & models.Q(market__isnull=False)
                        & models.Q(location__isnull=True)
                    )
                    | (
                        models.Q(region__isnull=True)
                        & models.Q(market__isnull=True)
                        & models.Q(location__isnull=False)
                    )
                ),
                name="scope_assignment_exactly_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="membershipscopeassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(region__isnull=False),
                fields=("membership", "region"),
                name="scope_assignment_no_dup_region",
            ),
        ),
        migrations.AddConstraint(
            model_name="membershipscopeassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(market__isnull=False),
                fields=("membership", "market"),
                name="scope_assignment_no_dup_market",
            ),
        ),
        migrations.AddConstraint(
            model_name="membershipscopeassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(location__isnull=False),
                fields=("membership", "location"),
                name="scope_assignment_no_dup_location",
            ),
        ),
        migrations.AddIndex(
            model_name="membershipscopeassignment",
            index=models.Index(
                fields=["membership"],
                name="mbr_scope_membership_idx",
            ),
        ),
    ]
