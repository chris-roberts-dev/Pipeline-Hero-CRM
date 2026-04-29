"""Initial migration: ImpersonationSession.

Hand-written rather than auto-generated to keep the M2 step 5 ship
self-contained, same approach as M2 steps 3 and 4.
"""

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from apps.platform.support.models import _generate_session_id


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImpersonationSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                (
                    "session_id",
                    models.CharField(
                        default=_generate_session_id,
                        editable=False,
                        max_length=64,
                        unique=True,
                    ),
                ),
                ("reason", models.TextField()),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ends_at", models.DateTimeField()),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("end_reason", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, null=True)),
                (
                    "support_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="impersonation_sessions_initiated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="impersonation_sessions_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="impersonation_sessions",
                        to="organizations.organization",
                    ),
                ),
                (
                    "target_membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="impersonation_sessions",
                        to="organizations.membership",
                    ),
                ),
                (
                    "ended_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="impersonation_sessions_ended",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "impersonation session",
                "verbose_name_plural": "impersonation sessions",
                "ordering": ["-started_at"],
            },
        ),
        migrations.AddIndex(
            model_name="impersonationsession",
            index=models.Index(
                fields=["support_user", "ended_at"],
                name="imp_support_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="impersonationsession",
            index=models.Index(
                fields=["target_user", "ended_at"],
                name="imp_target_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="impersonationsession",
            index=models.Index(
                fields=["target_organization", "-started_at"],
                name="imp_org_started_idx",
            ),
        ),
    ]
