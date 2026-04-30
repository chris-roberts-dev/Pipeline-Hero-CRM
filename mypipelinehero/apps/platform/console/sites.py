"""
Custom AdminSite implementation.

Spec §18.2 requires a custom AdminSite that groups apps into business
buckets and orders them deliberately. Django's default `admin.site` lists
apps alphabetically by app_label, which doesn't match the platform mental
model. Our implementation overrides `get_app_list()` to return the spec
§18.3 grouping.

Why a custom site rather than just decorating the default one?
  - The default `admin.site` is a shared global. Tests, third-party apps,
    and Django internals can register against it. Having our own site means
    "what does the admin show?" is a question with one well-defined answer
    that only our code controls.
  - Lets us mount it at a custom URL (`/admin/`) without conflicting with
    other Django admin patterns, and lets us swap it out in the future.

Auth:
  Inherits Django's standard admin auth — requires `is_active=True` and
  `is_staff=True`. The login view is the standard Django admin login.
  Future: a "platform staff" capability check can be layered on top once
  the platform-staff role exists (M2 step 5 added the capability codes;
  step 6 ships the AdminSite that uses them).

Permissions:
  Each ModelAdmin enforces its own add/change/delete permissions. By
  default, Django checks the user's Permission grants (the
  django.contrib.auth Permission system, separate from our RBAC). For
  read-only models (AuditEvent, ImpersonationSession), the ModelAdmin
  overrides permission methods to forbid mutations. For tenant-scoped
  models, the queryset is filtered by the user's superuser status — full
  admin access is currently superuser-only.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.contrib.admin import AdminSite
from django.http import HttpRequest


class PlatformAdminSite(AdminSite):
    """The custom AdminSite for the MyPipelineHero platform console."""

    site_title = "MyPipelineHero Console"
    site_header = "MyPipelineHero Platform Console"
    index_title = "Platform Administration"

    # Mounted at `/admin/` in config/urls.py. The login URL uses Django's
    # standard admin login at `/admin/login/`.
    site_url = "/"  # the "View site" link points back to the public site

    # Spec §18.3: grouping by business bucket. Each bucket lists model
    # labels (`<app_label>.<model_name>`) in display order. Apps not
    # listed below get appended in a final "Other" group — keeps the
    # site self-healing if a new model is registered without updating
    # this map.
    APP_GROUPS: dict[str, list[str]] = {
        "Platform": [
            "accounts.user",
            "organizations.organization",
            "organizations.membership",
            "rbac.membershipscopeassignment",
            "rbac.role",
            "rbac.capability",
            "rbac.membershiprole",
            "rbac.membershipcapabilitygrant",
            "rbac.rolecapability",
            "audit.auditevent",
            "support.impersonationsession",
        ],
        "CRM": [
            # Empty until M3+. Listed for spec §18.3 conformance — the
            # bucket header will appear empty until models register.
        ],
        "Catalog": [
            # M3 step 1
            "catalog_services.servicecategory",
            "catalog_services.service",
            "catalog_products.product",
            # M3 step 2
            "catalog_materials.rawmaterial",
            "catalog_suppliers.supplier",
            "catalog_suppliers.supplierproduct",
            # M3 step 3
            "catalog_manufacturing.bom",
            "catalog_manufacturing.bomline",
            # M3 step 4a
            "catalog_pricing.pricingrule",
            "catalog_pricing.pricingsnapshot",
        ],
        "Operations": [
            "locations.region",
            "locations.market",
            "locations.location",
            # Future: purchasing, build, workorders models in M5+.
        ],
        "Reporting": [
            # Empty until M6.
        ],
    }

    def get_app_list(
        self, request: HttpRequest, app_label: str | None = None
    ) -> list[dict]:
        """Return models grouped per spec §18.3, in deliberate order.

        Default Django behavior groups by `app_label` alphabetically. We
        flatten across apps and re-group by business bucket. Each model
        within a bucket is ordered per the APP_GROUPS list; models
        registered but not listed in any bucket fall through to "Other".
        """
        # Collect every registered model with its base metadata. We can't
        # use the parent's get_app_list() because it pre-groups by
        # app_label; we need the flat list of models.
        all_models = list(self._iter_registered_models(request))

        # Index by `<app_label>.<model_name>` for lookup against APP_GROUPS.
        by_label = {
            f"{m['app_label']}.{m['object_name'].lower()}": m for m in all_models
        }

        result: list[dict] = []
        seen: set[str] = set()

        for bucket_name, label_list in self.APP_GROUPS.items():
            models_in_bucket: list[dict] = []
            for label in label_list:
                if label in by_label:
                    models_in_bucket.append(by_label[label])
                    seen.add(label)
                # Silently skip labels not yet registered — empty buckets
                # are valid (spec §18.3 lists models that don't ship
                # until later milestones).

            # Skip empty buckets in the rendered output. Without this, the
            # CRM/Catalog/Reporting headers would display with no content,
            # which is uglier than just hiding them.
            if not models_in_bucket:
                continue

            result.append(
                {
                    "name": bucket_name,
                    # `app_label` is required by Django's templates; we use
                    # the bucket name lowercased for stability.
                    "app_label": bucket_name.lower(),
                    "app_url": "",  # bucket isn't itself a URL
                    "has_module_perms": True,
                    "models": models_in_bucket,
                }
            )

        # Anything registered but not assigned to a bucket — surface it
        # under "Other" so it's reachable rather than silently lost.
        unassigned = [m for label, m in by_label.items() if label not in seen]
        if unassigned:
            result.append(
                {
                    "name": "Other",
                    "app_label": "other",
                    "app_url": "",
                    "has_module_perms": True,
                    "models": unassigned,
                }
            )

        return result

    def get_urls(self):
        """Add custom URLs to the admin site.

        Overrides:
          - `logout`: routed to `apps.web.landing.views.logout_view`
            instead of Django's default admin logout. Reasons:
              * Default admin logout renders `admin/logged_out.html`,
                inconsistent with our convention of redirecting to "/"
              * Default admin logout doesn't emit our LOGOUT_ROOT audit
                event — a real auditing hole
            Replacing the URL (rather than overriding the `logout()`
            method) keeps the capability-coverage CI test happy because
            `logout_view` already carries `@no_capability_required`.

        Custom routes:
          - `support/impersonationsession/start/`: form-based start
            for impersonation sessions

        These URLs are namespaced under the AdminSite (`console:`) and
        use Django's standard staff_member_required auth gate from inside
        the views. Adding URLs here means they appear in
        `reverse("console:...")` resolution and inherit the admin's URL
        prefix (`/admin/`).
        """
        from django.urls import path

        from apps.platform.console import views as console_views
        from apps.web.landing.views import logout_view

        custom_urls = [
            # Override Django admin's default logout. Must come BEFORE
            # super().get_urls() because URL resolution is first-match.
            path("logout/", logout_view, name="logout"),
            path(
                "support/impersonationsession/start/",
                self.admin_view(console_views.start_impersonation_view),
                name="support_impersonationsession_start",
            ),
        ]
        # Custom URLs must go BEFORE the standard ones so Django doesn't
        # try to resolve our custom path as a model PK.
        return custom_urls + super().get_urls()

    def _iter_registered_models(self, request: HttpRequest) -> Iterable[dict]:
        """Yield admin-display dicts for every model registered with this site
        that the user is allowed to see.

        Mirrors the relevant subset of Django's `AdminSite._build_app_dict`
        but flattened — we don't pre-group by app_label, that's our job in
        get_app_list().
        """
        for model, model_admin in self._registry.items():
            perms = model_admin.get_model_perms(request)
            if not any(perms.values()):
                # User has no permissions on this model — Django's default
                # behavior is to omit it from the index.
                continue

            info = (model._meta.app_label, model._meta.model_name)
            model_dict = {
                "model": model,
                "name": model._meta.verbose_name_plural.title(),
                "object_name": model._meta.object_name,
                "perms": perms,
                "admin_url": None,
                "add_url": None,
                "app_label": model._meta.app_label,
            }
            if perms.get("change") or perms.get("view"):
                try:
                    model_dict["admin_url"] = self._registry[model].get_view_on_site_url
                except Exception:
                    pass
                # Reverse changelist URL.
                from django.urls import reverse

                try:
                    model_dict["admin_url"] = reverse(
                        f"{self.name}:%s_%s_changelist" % info,
                        current_app=self.name,
                    )
                except Exception:
                    model_dict["admin_url"] = None
            if perms.get("add"):
                from django.urls import reverse

                try:
                    model_dict["add_url"] = reverse(
                        f"{self.name}:%s_%s_add" % info,
                        current_app=self.name,
                    )
                except Exception:
                    model_dict["add_url"] = None

            yield model_dict


# Module-level singleton. Importing `console_site` from anywhere registers
# against the same instance. Models register via the standard
# `console_site.register(Model, ModelAdmin)` pattern.
console_site = PlatformAdminSite(name="console")
