"""Tests for TenancyMiddleware — host parsing, org resolution, caching."""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.common.tenancy.middleware import (
    TenancyMiddleware,
    _resolve_slug_from_host,
)
from apps.platform.organizations.models import Organization


# ---------------------------------------------------------------------------
# Host parsing — pure function, no DB or cache
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host,expected_slug",
    [
        ("mypipelinehero.localhost", None),                    # root domain
        ("mypipelinehero.localhost:80", None),                 # port is stripped
        ("acme.mypipelinehero.localhost", "acme"),             # subdomain
        ("ACME.MYPIPELINEHERO.LOCALHOST", "acme"),             # case-insensitive
        ("beta.mypipelinehero.localhost:8000", "beta"),        # subdomain + port
        ("example.com", None),                                 # unrelated domain
        ("", None),                                            # empty
        (".mypipelinehero.localhost", None),                   # malformed empty label
    ],
)
def test_resolve_slug_from_host(host: str, expected_slug) -> None:
    assert _resolve_slug_from_host(host, "mypipelinehero.localhost") == expected_slug


# ---------------------------------------------------------------------------
# Middleware integration — needs DB + cache
# ---------------------------------------------------------------------------


@pytest.fixture
def middleware():
    # Trivial get_response shim — we don't exercise the downstream view.
    return TenancyMiddleware(get_response=lambda request: request)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestMiddlewareIntegration:
    def test_root_domain_sets_organization_none(self, middleware) -> None:
        request = RequestFactory().get("/", HTTP_HOST="mypipelinehero.localhost")
        middleware(request)
        assert request.organization is None

    def test_active_subdomain_resolves_to_org(self, middleware) -> None:
        org = Organization.objects.create(name="Acme", slug="acme")
        request = RequestFactory().get("/", HTTP_HOST="acme.mypipelinehero.localhost")
        middleware(request)
        assert request.organization is not None
        assert request.organization.pk == org.pk

    def test_inactive_org_resolves_to_none(self, middleware) -> None:
        # Spec §9.2: invalid, inactive, or unauthorized tenant routes must fail safely.
        Organization.objects.create(
            name="Beta", slug="beta", status=Organization.Status.INACTIVE
        )
        request = RequestFactory().get("/", HTTP_HOST="beta.mypipelinehero.localhost")
        middleware(request)
        assert request.organization is None

    def test_unknown_slug_resolves_to_none(self, middleware) -> None:
        request = RequestFactory().get("/", HTTP_HOST="nobody.mypipelinehero.localhost")
        middleware(request)
        assert request.organization is None

    def test_unknown_slug_is_negatively_cached(self, middleware) -> None:
        # Spec §9.2: slug lookup must be cached. Negative caching is important
        # to avoid DB hits on every bad-slug request.
        request1 = RequestFactory().get("/", HTTP_HOST="ghost.mypipelinehero.localhost")
        middleware(request1)

        # Second request for the same unknown slug should hit cache.
        # We verify by instrumenting the fetch method.
        call_count = {"n": 0}
        original = TenancyMiddleware._fetch_active_by_slug

        def counting_fetch(slug):
            call_count["n"] += 1
            return original(slug)

        # Monkey-patch via module to avoid staticmethod descriptor pitfalls.
        import apps.common.tenancy.middleware as mw_mod

        mw_mod.TenancyMiddleware._fetch_active_by_slug = staticmethod(counting_fetch)
        try:
            request2 = RequestFactory().get(
                "/", HTTP_HOST="ghost.mypipelinehero.localhost"
            )
            middleware(request2)
            assert call_count["n"] == 0, "Second request should have hit cache"
        finally:
            mw_mod.TenancyMiddleware._fetch_active_by_slug = staticmethod(original)
