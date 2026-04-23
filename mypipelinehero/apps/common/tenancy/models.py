"""
Abstract base for tenant-owned models.

Models that inherit `TenantModel` automatically get:
  - an `organization` FK (required, PROTECT)
  - `TenantManager` as the default manager (with `.for_org(org)`)
  - `created_at` / `updated_at` audit timestamps

Models that need *additional* manager methods should subclass `TenantManager`
in their own app rather than reassigning `objects`, otherwise the CI coverage
test (apps/common/tests/test_tenant_manager_coverage.py) will flag them.

Why PROTECT on organization?
----------------------------
An Organization is the tenant. Deleting an organization should never
cascade-delete live business records — that's the kind of thing that causes
irreversible data loss. If an org is truly being removed, it happens via an
explicit offboarding workflow (not in v1 scope), not via `delete()`.
"""

from __future__ import annotations

from django.db import models

from .managers import TenantManager


class TenantModel(models.Model):
    """Abstract base class for every tenant-owned (organization-scoped) record.

    Usage:
        class Lead(TenantModel):
            name = models.CharField(...)
            # organization, created_at, updated_at come from TenantModel
            # objects is TenantManager by inheritance
    """

    organization = models.ForeignKey(
        # String reference avoids importing Organization at module load time
        # and keeps this base class usable from anywhere in the tree.
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="+",  # suppress reverse accessor; each model defines its own
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True
        # Default ordering is deliberately NOT set here. Per-domain models
        # should set ordering explicitly on their own Meta to avoid surprising
        # query costs (unordered-model queries become ORDER BY id by default,
        # which is often the wrong thing).
