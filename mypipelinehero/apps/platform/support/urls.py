"""URL routes for the support app.

Mounted at the tenant-portal URL prefix because end-impersonation must
work on tenant subdomains (where impersonation sessions are active).
The platform-side start UI lives separately on the root domain when M2
step 6 ships the admin console.
"""

from django.urls import path

from apps.platform.support import views

app_name = "support"

urlpatterns = [
    path(
        "_/end-impersonation/",
        views.end_impersonation_view,
        name="end_impersonation",
    ),
]
