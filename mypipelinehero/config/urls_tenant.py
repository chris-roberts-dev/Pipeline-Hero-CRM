"""
Tenant-subdomain URL configuration.

Selected by TenancyMiddleware when the Host header resolves to an active
organization. Exposes ONLY the tenant portal — the login landing page and
org picker live exclusively on the root domain.
"""

from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", include("apps.web.tenant_portal.urls")),
]

if settings.DEBUG:
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [
            path("__debug__/", include("debug_toolbar.urls")),
        ]
    except ImportError:
        pass
