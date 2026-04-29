"""
Tenant-subdomain URL configuration.

Selected by TenancyMiddleware when the Host header resolves to an active
organization. Exposes ONLY the tenant portal — the login landing page and
org picker live exclusively on the root domain.
"""

from django.http import JsonResponse
from django.urls import include, path

from apps.platform.rbac.decorators import no_capability_required


@no_capability_required(
    reason="Liveness probe; must remain accessible from any context."
)
def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", include("apps.web.tenant_portal.urls")),
    # Support tooling that needs to run on the tenant subdomain. Currently
    # just end-impersonation (banner button); start-impersonation lives on
    # the root domain when the platform admin console ships in M2 step 6.
    path("", include("apps.platform.support.urls")),
]

# See config/urls.py for the same rationale. Included in the tenant URLconf
# too because TenancyMiddleware swaps request.urlconf to this module for
# tenant-subdomain requests, and the debug toolbar middleware reverses
# against request.urlconf — so djdt must be registered here independently.
try:
    import debug_toolbar  # noqa: F401

    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
except ImportError:
    pass
