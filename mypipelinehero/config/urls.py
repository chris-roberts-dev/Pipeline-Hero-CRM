"""
Root URL configuration (root domain: mypipelinehero.localhost).

Used for requests where TenancyMiddleware did NOT resolve a tenant
subdomain. Tenant-subdomain requests use `config/urls_tenant.py`, which
is selected per-request by TenancyMiddleware via `request.urlconf`.

This separation is Django's recommended pattern for host-based URL
dispatch. It also prevents accidental cross-mounting — root URL patterns
are simply unreachable on a tenant subdomain and vice versa.
"""

from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", include("apps.web.landing.urls")),
    path("", include("apps.web.auth_portal.urls")),
]

# Debug toolbar — only when available and in DEBUG.
if settings.DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [
            path("__debug__/", include("debug_toolbar.urls")),
        ]
    except ImportError:
        pass
