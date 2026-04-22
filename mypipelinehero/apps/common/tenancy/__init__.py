"""Tenancy base package.

Re-exports the managers at package level for ergonomics. DOES NOT re-export
TenantModel — importing a models.Model subclass at package init time runs
before Django's app registry is ready and raises AppRegistryNotReady during
startup. Consumers import TenantModel directly:

    from apps.common.tenancy.models import TenantModel

Managers are safe to re-export here because they don't register with the
app registry — they're just Python classes.
"""

from .managers import TenantManager, TenantQuerySet

__all__ = ["TenantManager", "TenantQuerySet"]
