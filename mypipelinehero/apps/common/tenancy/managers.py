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

    def for_org(self, organization: Organization | int | Any) -> TenantQuerySet:
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
