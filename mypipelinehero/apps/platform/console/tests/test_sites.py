"""Tests for the custom AdminSite.

Covers:
  - All expected models are registered with the site
  - get_app_list() groups per spec §18.3 with deliberate ordering
  - Read-only ModelAdmins forbid mutations
  - The site's URLs resolve under the `console:` namespace
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from apps.platform.console.admin import (
    AuditEventAdmin,
    CapabilityAdmin,
    ImpersonationSessionAdmin,
)
from apps.platform.console.sites import console_site

User = get_user_model()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="root@example.com", password="x" * 12)


@pytest.fixture
def request_factory():
    return RequestFactory()


# ---------------------------------------------------------------------------
# Site registration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistrationCoverage:
    """Every model that should be in admin actually is."""

    EXPECTED_MODELS = [
        ("accounts", "user"),
        ("organizations", "organization"),
        ("organizations", "membership"),
        ("rbac", "capability"),
        ("rbac", "role"),
        ("rbac", "rolecapability"),
        ("rbac", "membershiprole"),
        ("rbac", "membershipcapabilitygrant"),
        ("rbac", "membershipscopeassignment"),
        ("audit", "auditevent"),
        ("support", "impersonationsession"),
        ("locations", "region"),
        ("locations", "market"),
        ("locations", "location"),
    ]

    def test_every_expected_model_is_registered(self):
        registered = {
            (m._meta.app_label, m._meta.model_name) for m in console_site._registry
        }
        missing = set(self.EXPECTED_MODELS) - registered
        assert (
            not missing
        ), f"Expected models not registered with console_site: {missing}"


# ---------------------------------------------------------------------------
# get_app_list grouping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAppListGrouping:
    def test_returns_business_buckets_not_django_apps(self, request_factory, superuser):
        request = request_factory.get("/admin/")
        request.user = superuser

        app_list = console_site.get_app_list(request)
        bucket_names = [bucket["name"] for bucket in app_list]

        # Platform should be present (has registered models).
        assert "Platform" in bucket_names
        # Operations should be present (has Region/Market/Location).
        assert "Operations" in bucket_names
        # CRM, Catalog, Reporting are empty in v1 → omitted entirely.
        assert "CRM" not in bucket_names
        assert "Catalog" not in bucket_names
        assert "Reporting" not in bucket_names

    def test_platform_bucket_contains_user_org_and_audit(
        self, request_factory, superuser
    ):
        request = request_factory.get("/admin/")
        request.user = superuser

        app_list = console_site.get_app_list(request)
        platform = next(b for b in app_list if b["name"] == "Platform")
        model_labels = [
            f"{m['app_label']}.{m['object_name'].lower()}" for m in platform["models"]
        ]

        assert "accounts.user" in model_labels
        assert "organizations.organization" in model_labels
        assert "audit.auditevent" in model_labels
        assert "support.impersonationsession" in model_labels

    def test_operations_bucket_contains_locations(self, request_factory, superuser):
        request = request_factory.get("/admin/")
        request.user = superuser

        app_list = console_site.get_app_list(request)
        ops = next(b for b in app_list if b["name"] == "Operations")
        model_labels = [
            f"{m['app_label']}.{m['object_name'].lower()}" for m in ops["models"]
        ]
        assert "locations.region" in model_labels
        assert "locations.market" in model_labels
        assert "locations.location" in model_labels

    def test_models_within_bucket_keep_declared_order(self, request_factory, superuser):
        # Spec §18.4: models display in deliberate order, not alphabetical.
        # Platform bucket lists user FIRST, then organization, then membership.
        # Verify this rather than alphabetical ('membership' would come first).
        request = request_factory.get("/admin/")
        request.user = superuser

        app_list = console_site.get_app_list(request)
        platform = next(b for b in app_list if b["name"] == "Platform")
        labels = [
            f"{m['app_label']}.{m['object_name'].lower()}" for m in platform["models"]
        ]
        # User comes before Organization comes before Membership.
        assert labels.index("accounts.user") < labels.index(
            "organizations.organization"
        )
        assert labels.index("organizations.organization") < labels.index(
            "organizations.membership"
        )


# ---------------------------------------------------------------------------
# Read-only enforcement
# ---------------------------------------------------------------------------


class TestReadOnlyAdmins:
    """Audit and ImpersonationSession admin must forbid mutations."""

    def _check_readonly(self, admin_class):
        admin_inst = admin_class.__new__(admin_class)  # don't need full init
        # Mock request; the methods don't actually use it.
        request = object()
        assert admin_inst.has_add_permission(request) is False
        assert admin_inst.has_change_permission(request) is False
        assert admin_inst.has_delete_permission(request) is False

    def test_audit_event_is_readonly(self):
        self._check_readonly(AuditEventAdmin)

    def test_impersonation_session_is_readonly(self):
        self._check_readonly(ImpersonationSessionAdmin)

    def test_capability_is_readonly(self):
        # Capabilities are platform-defined data; admins shouldn't add or
        # edit them — that would bypass the registry's import-time
        # consistency check.
        self._check_readonly(CapabilityAdmin)


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


class TestUrlResolution:
    """The `console:` namespace must resolve standard admin URLs and our
    custom start-impersonation URL."""

    def test_admin_index_resolves(self):
        url = reverse("console:index")
        assert url.startswith("/admin/")

    def test_admin_login_resolves(self):
        url = reverse("console:login")
        assert url.startswith("/admin/login/")

    def test_user_changelist_resolves(self):
        # Standard model changelist URL via the AdminSite namespace.
        url = reverse("console:accounts_user_changelist")
        assert url.startswith("/admin/accounts/user/")

    def test_organization_changelist_resolves(self):
        url = reverse("console:organizations_organization_changelist")
        assert url.startswith("/admin/organizations/organization/")

    def test_impersonation_session_changelist_resolves(self):
        url = reverse("console:support_impersonationsession_changelist")
        assert url.startswith("/admin/support/impersonationsession/")

    def test_start_impersonation_url_resolves(self):
        # The custom view we added via get_urls().
        url = reverse("console:support_impersonationsession_start")
        assert url == "/admin/support/impersonationsession/start/"

    def test_only_console_site_mounted_not_default_admin_site(self):
        # Django's default `admin.site` global exists (it's a module-level
        # singleton in django.contrib.admin) and `admin.autodiscover` auto-
        # registers third-party apps' admin.py against it. That's harmless
        # *as long as it's not mounted in URLs* — which we never do.
        #
        # Both `console:index` and `admin:index` resolve to the same URL
        # `/admin/` because Django's AdminSite always reports app_name="admin"
        # in addition to the instance name. The instance-namespace is `console`,
        # the app-namespace is `admin`. They reach the same site.
        #
        # What this test really guards against: someone mounting
        # `admin.site.urls` in addition to `console_site.urls`. If they did,
        # we'd have TWO AdminSites at different URL prefixes and the apparent
        # "single console" would actually be split.
        from django.urls import get_resolver

        resolver = get_resolver()

        # Count how many distinct URL prefixes have an AdminSite registered.
        # Each AdminSite include tuple has app_name="admin"; we only want one.
        admin_resolvers = resolver.app_dict.get("admin", [])
        assert len(admin_resolvers) == 1, (
            f"Expected exactly one AdminSite mounted in URLs; found "
            f"{len(admin_resolvers)}. Did someone add `admin.site.urls` "
            f"alongside `console_site.urls`?"
        )

        # And the one that's mounted should be ours, not the default.
        # Instance namespace is the way to identify it.
        assert "console" in resolver.namespace_dict
        # The default site uses instance_name="admin" (same as app_name).
        # If "admin" is in namespace_dict, the default site got mounted.
        assert "admin" not in resolver.namespace_dict, (
            "django.contrib.admin.site appears to be mounted in URLs. "
            "Only console_site should be mounted."
        )


@pytest.mark.django_db
class TestAdminLogoutBehavior:
    """The admin's logout link (rendered by Django's admin templates as
    `/admin/logout/`) must use our standard logout flow: redirect to "/"
    and emit the LOGOUT_ROOT audit event.

    Django's default `AdminSite.logout()` renders `admin/logged_out.html`
    — a different post-logout experience than the rest of the app, and
    no audit event. Our PlatformAdminSite.logout() override delegates
    to `apps.web.landing.views.logout_view` for consistency.
    """

    def test_admin_logout_redirects_to_root(self):
        from django.test import Client

        from apps.platform.audit.models import AuditEvent

        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="x" * 12,
        )
        client = Client(HTTP_HOST="mypipelinehero.localhost")
        client.force_login(admin)

        # Hit the admin's logout endpoint.
        resp = client.post("/admin/logout/")

        # Should redirect to "/", not render admin/logged_out.html.
        assert resp.status_code == 302
        assert resp["Location"] == "/"

        # Audit event was emitted (the default admin logout doesn't do this).
        assert AuditEvent.objects.filter(
            event_type="LOGOUT_ROOT",
            actor_user=admin,
        ).exists()
