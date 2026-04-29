"""Initial migration: Region, Market, Location.

Hand-written rather than auto-generated to keep the M2 step 4 ship
self-contained, same approach as M2 step 3's MembershipRole migration.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Region",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(blank=True, max_length=20)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "region",
                "verbose_name_plural": "regions",
                "ordering": ["organization__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="Market",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(blank=True, max_length=20)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="markets",
                        to="locations.region",
                    ),
                ),
            ],
            options={
                "verbose_name": "market",
                "verbose_name_plural": "markets",
                "ordering": ["region__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(blank=True, max_length=20)),
                ("address", models.TextField(blank=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
                (
                    "market",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="locations",
                        to="locations.market",
                    ),
                ),
            ],
            options={
                "verbose_name": "location",
                "verbose_name_plural": "locations",
                "ordering": ["market__region__name", "market__name", "name"],
            },
        ),
        # Region constraints
        migrations.AddConstraint(
            model_name="region",
            constraint=models.UniqueConstraint(
                fields=("organization", "name"),
                name="region_org_name_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="region",
            constraint=models.UniqueConstraint(
                condition=~models.Q(code=""),
                fields=("organization", "code"),
                name="region_org_code_unique",
            ),
        ),
        # Market constraints
        migrations.AddConstraint(
            model_name="market",
            constraint=models.UniqueConstraint(
                fields=("region", "name"),
                name="market_region_name_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="market",
            constraint=models.UniqueConstraint(
                condition=~models.Q(code=""),
                fields=("organization", "code"),
                name="market_org_code_unique",
            ),
        ),
        # Location constraints
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(
                fields=("market", "name"),
                name="location_market_name_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(
                condition=~models.Q(code=""),
                fields=("organization", "code"),
                name="location_org_code_unique",
            ),
        ),
    ]
