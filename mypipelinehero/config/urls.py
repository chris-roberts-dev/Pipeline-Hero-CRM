"""
Root URL configuration (root domain: mypipelinehero.localhost).

Used for requests where TenancyMiddleware did NOT resolve a tenant
subdomain. Tenant-subdomain requests use `config/urls_tenant.py`, which
is selected per-request by TenancyMiddleware via `request.urlconf`.

This separation is Django's recommended pattern for host-based URL
dispatch. It also prevents accidental cross-mounting — root URL patterns
are simply unreachable on a tenant subdomain and vice versa.
"""

from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", include("apps.web.landing.urls")),
    path("", include("apps.web.auth_portal.urls")),
]

# Register debug-toolbar URLs whenever the module is importable. This is
# broader than the usual "only in DEBUG" pattern because the toolbar's
# middleware (if active) calls reverse("djdt:...") regardless of DEBUG, and
# missing the namespace crashes the request. Harmless when the middleware
# is disabled — the URLs just sit unused.
try:
    import debug_toolbar  # noqa: F401
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
except ImportError:
    pass
