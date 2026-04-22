from __future__ import annotations

import logging
from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


def _cache_key(slug: str) -> str:
    # Prefix the key so we can bump ALL cached slugs in one operation
    # (cache.delete_pattern or a version key) if we ever need a global flush.
    return f"tenancy:org_by_slug:v1:{slug}"


def _resolve_slug_from_host(host: str, root_domain: str) -> str | None:
    """Given `Host` header and the configured root domain, return the subdomain
    slug or None.

        mypipelinehero.localhost          -> None (root domain)
        acme.mypipelinehero.localhost     -> "acme"
        www.mypipelinehero.localhost      -> "www" (caller decides if reserved)
        unrelated.example.com             -> None (not our domain)

    Host may include a port (e.g. `acme.mypipelinehero.localhost:80`) which
    we strip here. Comparison is case-insensitive because DNS is.
    """
    host = host.lower().split(":", 1)[0]
    root = root_domain.lower()

    if host == root:
        return None

    suffix = f".{root}"
    if host.endswith(suffix):
        slug = host[: -len(suffix)]
        # Guard against `.mypipelinehero.localhost` with an empty label —
        # shouldn't happen but defensive.
        return slug if slug else None

    # Host doesn't match our root domain at all — probably a misconfigured
    # deployment or a direct-IP request. No tenant context.
    return None


class TenancyMiddleware:
    """Attach `request.organization` based on the subdomain in the Host header.

    Placement: after SessionMiddleware and AuthenticationMiddleware, because
    some downstream authorization logic may want both user AND organization
    in a single check. Order is defined in config/settings/base.py.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Default to None. Views that require a tenant context check this
        # explicitly rather than relying on middleware to 404 for them —
        # cleaner separation of concerns.
        request.organization = None  # type: ignore[attr-defined]

        host = request.get_host()
        slug = _resolve_slug_from_host(host, settings.ROOT_DOMAIN)

        if slug is not None:
            org = self._get_active_org_by_slug(slug)
            if org is not None:
                request.organization = org  # type: ignore[attr-defined]
                # Swap the URLconf to the tenant tree. This is Django's
                # supported mechanism for host-based URL dispatch — setting
                # `request.urlconf` takes precedence over settings.ROOT_URLCONF
                # for this request only.
                request.urlconf = "config.urls_tenant"
            else:
                # Log but don't block — the view layer decides how to respond
                # (404 page, redirect to root, etc.). This runs on every request
                # to an unknown subdomain so keep the log level INFO not WARNING.
                logger.info(
                    "tenancy: unknown or inactive slug %r on host %r", slug, host
                )
                # Unknown subdomain: route via root URL tree so the 404 page
                # is rendered by root-domain handlers, and the user can still
                # reach `/login/` to recover.
                # (No urlconf override needed — root is the default.)

        return self.get_response(request)

    def _get_active_org_by_slug(self, slug: str):
        """Resolve slug → Organization, using a short-TTL cache.

        Returns None for unknown or non-ACTIVE orgs. Cache stores both hits
        and misses to avoid a DB round-trip on every bad-slug request (which
        would otherwise be a trivial DoS amplifier).
        """
        key = _cache_key(slug)
        cached = cache.get(key, default=_MISS_SENTINEL)
        if cached is not _MISS_SENTINEL:
            # Cached value may be None (negative cache) or an Organization pk.
            # We re-fetch from DB on pk hit to get a fresh instance; fetching
            # by pk is cheap and we avoid caching a full serialized model
            # which can go stale in confusing ways.
            if cached is None:
                return None
            return self._fetch_active_by_pk(cached)

        org = self._fetch_active_by_slug(slug)
        cache.set(
            key,
            org.pk if org is not None else None,
            timeout=settings.ORG_SLUG_CACHE_TTL_SECONDS,
        )
        return org

    @staticmethod
    def _fetch_active_by_slug(slug: str):
        # Local import to avoid a circular dependency at module import time —
        # middleware is loaded during Django setup, Organizations app isn't
        # guaranteed to be ready yet.
        from apps.platform.organizations.models import Organization

        return (
            Organization.objects.filter(slug=slug, status=Organization.Status.ACTIVE)
            .only("id", "slug", "name", "status")
            .first()
        )

    @staticmethod
    def _fetch_active_by_pk(pk: int):
        from apps.platform.organizations.models import Organization

        return (
            Organization.objects.filter(pk=pk, status=Organization.Status.ACTIVE)
            .only("id", "slug", "name", "status")
            .first()
        )


# Sentinel used to distinguish "cache miss" from "cached None value".
# A plain `cache.get(key)` returns None on miss, which is ambiguous when
# None is also a legitimate cached value (negative cache).
_MISS_SENTINEL = object()
