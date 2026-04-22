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
