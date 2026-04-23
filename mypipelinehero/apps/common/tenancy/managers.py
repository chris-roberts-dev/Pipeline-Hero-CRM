"""
Tenancy managers and querysets.

Every tenant-owned model uses `TenantManager` as its default manager. This gives
every queryset a `for_org(org)` method that scopes results to a single
organization. Tenant scoping is ALSO enforced at the service layer — this
manager is a defense in depth, not the only line of defense.

Why not auto-scope every query?
-------------------------------
Tempting, but wrong. Auto-scoping requires thread-locals or request-local state,
which breaks Celery workers, management commands, shell sessions, and tests.
It also hides the tenancy boundary from readers of the code: a `Lead.objects.all()`
call looks safe but is actually scoped by some middleware you can't see. Explicit
`for_org(org)` is a readability win and a correctness win.

The CI test in apps/common/tests/test_tenant_manager_coverage.py enumerates every
model with an `organization` FK and asserts its default manager is a TenantManager
(or subclass). That's how we prevent someone from quietly adding a new model
with `objects = models.Manager()` and bypassing tenancy checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models

if TYPE_CHECKING:
    # Forward reference — Organization lives in apps.platform.organizations
    # and importing it here would create a circular dependency. TYPE_CHECKING
    # only runs under mypy, not at import time.
    from apps.platform.organizations.models import Organization


class TenantQuerySet(models.QuerySet):
    """QuerySet that adds tenant-scoping helpers.

    All tenant-owned models get a manager backed by this queryset, which means
    every manager method returns a `TenantQuerySet` and `for_org(...)` is
    chainable with the usual Django queryset API (`filter`, `order_by`, etc).
    """

    def for_org(self, organization: "Organization | int | Any") -> "TenantQuerySet":
        """Restrict the queryset to records belonging to a single organization.

        Accepts either an Organization instance or a primary key value. Using
        a pk avoids a needless lookup when the caller already has the id.

        This is the ONLY sanctioned way for views, services, and serializers
        to begin a tenant-scoped query. Calling `.filter(organization=...)`
        directly works but bypasses the naming convention that makes tenant
        scoping grep-able across the codebase.
        """
        return self.filter(organization=organization)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):  # type: ignore[misc]
    """Default manager for every tenant-owned model.

    Inherits `for_org` from TenantQuerySet. Deliberately empty beyond that —
    extra per-domain manager methods belong on domain-specific subclasses
    (e.g. `LeadManager(TenantManager)`), not here.
    """

    # The `from_queryset` metaclass trick above generates a Manager class whose
    # methods proxy every TenantQuerySet method. This is the standard Django
    # idiom and it's what Django's docs recommend for custom managers.
    pass
