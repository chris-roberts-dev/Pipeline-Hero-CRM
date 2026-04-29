"""End-to-end integration tests for the full login -> handoff -> tenant flow.

These tests exercise views (not just services) and assert the full user
journey works as a real browser would experience it. They do NOT verify
session cookie domain scoping — that's a browser-level behavior we can't
replicate in Django's test client — but they do verify every other piece
of the spec §9.4 flow:

    1. POST /login/ with valid credentials establishes root-domain session
    2. Single-org user is redirected to the handoff issuer
    3. Handoff issuer mints a token and redirects to the tenant subdomain
    4. Tenant subdomain's /auth/handoff?token=... establishes tenant session
    5. Tenant dashboard renders with the correct organization context
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.platform.organizations.models import Membership, Organization

User = get_user_model()

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def _clear_handoff_redis():
    import redis as redis_lib
    from django.conf import settings

    client = redis_lib.from_url(settings.HANDOFF_TOKEN_REDIS_URL, decode_responses=True)
    client.flushdb()
    yield
    client.flushdb()


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", password=PASSWORD)


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme Corp", slug="acme")


@pytest.fixture
def membership(db, user, org):
    return Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )


@pytest.mark.django_db
class TestSingleOrgFlow:
    """Single-org user: login -> handoff issuer -> tenant dashboard."""

    def test_root_login_redirects_to_handoff_issuer(self, user, org, membership):
        c = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = c.post("/login/", {"email": user.email, "password": PASSWORD})
        assert resp.status_code == 302
        assert "/auth/handoff/" in resp["Location"]
        assert f"org={org.pk}" in resp["Location"]

    def test_handoff_issuer_redirects_to_tenant_subdomain(self, user, org, membership):
        c = Client(HTTP_HOST="mypipelinehero.localhost")
        c.post("/login/", {"email": user.email, "password": PASSWORD})

        resp = c.get("/auth/handoff/", {"org": org.pk})
        assert resp.status_code == 302
        location = resp["Location"]
        parsed = urlparse(location)

        # Redirect target is on the tenant subdomain.
        assert parsed.hostname == "acme.mypipelinehero.localhost"
        # With a token query param.
        assert "token" in parse_qs(parsed.query)

    def test_tenant_handoff_completion_establishes_session(self, user, org, membership):
        # 1. Login on root
        c = Client(HTTP_HOST="mypipelinehero.localhost")
        c.post("/login/", {"email": user.email, "password": PASSWORD})

        # 2. Hit the handoff issuer to get a token
        resp = c.get("/auth/handoff/", {"org": org.pk})
        parsed = urlparse(resp["Location"])
        token = parse_qs(parsed.query)["token"][0]

        # 3. Make a NEW client on the tenant subdomain — this mimics a browser
        # switching hosts (cookies don't carry).
        tenant = Client(HTTP_HOST="acme.mypipelinehero.localhost")
        resp = tenant.get("/auth/handoff", {"token": token})
        assert resp.status_code == 302
        # reverse() defaults to ROOT_URLCONF; the tenant-portal namespace lives
        # in config.urls_tenant and must be looked up there explicitly.
        assert resp["Location"] == reverse(
            "tenant_portal:dashboard", urlconf="config.urls_tenant"
        )

        # 4. The tenant client now has an authenticated session.
        dashboard_resp = tenant.get("/")
        assert dashboard_resp.status_code == 200
        assert b"Acme Corp" in dashboard_resp.content


@pytest.mark.django_db
class TestMultiOrgFlow:
    """Multi-org user: login -> org picker -> handoff."""

    def test_multi_org_user_sees_picker(self, user):
        org_a = Organization.objects.create(name="Alpha", slug="alpha")
        org_b = Organization.objects.create(name="Beta", slug="beta")
        Membership.objects.create(
            user=user, organization=org_a, status=Membership.Status.ACTIVE
        )
        Membership.objects.create(
            user=user, organization=org_b, status=Membership.Status.ACTIVE
        )

        c = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = c.post("/login/", {"email": user.email, "password": PASSWORD})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("auth_portal:pick_organization")

        picker = c.get(resp["Location"])
        assert picker.status_code == 200
        assert b"Alpha" in picker.content
        assert b"Beta" in picker.content


@pytest.mark.django_db
class TestAuthFailureModes:
    def test_invalid_credentials_renders_error(self, db):
        c = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = c.post("/login/", {"email": "nobody@example.com", "password": "wrong"})
        assert resp.status_code == 401
        assert b"Invalid email or password" in resp.content

    def test_no_membership_user_renders_no_access(self, user):
        # Authenticated user with no memberships: dead-end page.
        c = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = c.post("/login/", {"email": user.email, "password": PASSWORD})
        assert resp.status_code == 403
        assert b"not a member of any active organization" in resp.content

    def test_tenant_subdomain_rejects_unknown_token(self, org):
        c = Client(HTTP_HOST="acme.mypipelinehero.localhost")
        resp = c.get("/auth/handoff", {"token": "garbage"})
        assert resp.status_code == 401
        assert b"invalid or has expired" in resp.content

    def test_tenant_dashboard_without_session_redirects_to_root_login(self, org):
        c = Client(HTTP_HOST="acme.mypipelinehero.localhost")
        resp = c.get("/")
        assert resp.status_code == 302
        # Redirected to root-domain login.
        assert "mypipelinehero.localhost/login/" in resp["Location"]

    def test_tenant_portal_urls_not_served_on_root_domain(self, db):
        # /auth/logout/ is a tenant_portal URL — on the root domain it must 404.
        c = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = c.get("/auth/logout/")
        assert resp.status_code == 404

    def test_root_login_url_not_served_on_tenant_subdomain(self, org):
        # /login/ is a landing URL — on a tenant subdomain it must 404.
        c = Client(HTTP_HOST="acme.mypipelinehero.localhost")
        resp = c.get("/login/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestPlatformUserRouting:
    """Spec: a logged-in user with is_staff or is_superuser (and no
    tenant memberships) should land in the platform admin console."""

    def test_superuser_with_no_memberships_redirects_to_admin(self, db):
        admin_user = User.objects.create_superuser(
            email="root@example.com",
            password=PASSWORD,
        )
        client = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = client.post("/login/", {"email": admin_user.email, "password": PASSWORD})
        assert resp.status_code == 302
        # Lands at the console index. We accept either a relative or
        # absolute URL since redirect() may emit either.
        assert resp["Location"].endswith("/admin/")

    def test_staff_user_with_no_memberships_redirects_to_admin(self, db):
        # is_staff alone (without is_superuser) is also a "platform user"
        # per is_platform_user. Same routing.
        staff_user = User.objects.create_user(
            email="staff@example.com",
            password=PASSWORD,
            is_staff=True,
        )
        client = Client(HTTP_HOST="mypipelinehero.localhost")
        resp = client.post("/login/", {"email": staff_user.email, "password": PASSWORD})
        assert resp.status_code == 302
        assert resp["Location"].endswith("/admin/")


@pytest.mark.django_db
class TestLogoutSemantics:
    def test_root_logout_redirects_to_root_url(self, user, org, membership):
        """Logout lands the user at "/" (root URL) for the post-logout
        marketing/landing experience. Today "/" 404s because nothing is
        mounted there — that's expected interim state until a public
        landing page ships. The important thing is the destination URL,
        which this test pins."""
        root = Client(HTTP_HOST="mypipelinehero.localhost")
        root.post("/login/", {"email": user.email, "password": PASSWORD})

        resp = root.get("/logout/")
        assert resp.status_code == 302
        assert resp["Location"] == "/"

    def test_root_logout_does_not_affect_tenant_session(self, user, org, membership):
        """Spec §9.4: root-domain logout terminates only the root session."""
        root = Client(HTTP_HOST="mypipelinehero.localhost")
        root.post("/login/", {"email": user.email, "password": PASSWORD})
        token_resp = root.get("/auth/handoff/", {"org": org.pk})
        token = parse_qs(urlparse(token_resp["Location"]).query)["token"][0]

        tenant = Client(HTTP_HOST="acme.mypipelinehero.localhost")
        tenant.get("/auth/handoff", {"token": token})

        # Both sessions active.
        assert root.get("/login/").status_code == 200  # root is GET-available
        assert tenant.get("/").status_code == 200

        # Logout from root.
        root.get("/logout/")

        # Tenant session must still be live. We can't test cookie scoping
        # here (same Client instance) but we can verify the tenant's
        # session entry wasn't deleted by the root-logout call.
        assert tenant.get("/").status_code == 200
