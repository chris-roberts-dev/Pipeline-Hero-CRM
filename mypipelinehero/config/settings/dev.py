"""
Development settings.

Loaded when DJANGO_SETTINGS_MODULE=config.settings.dev.
Optimized for fast feedback loops and readable output.
"""

from .base import *  # noqa: F401,F403
from .base import (  # explicit imports for things we mutate below
    INSTALLED_APPS,
    LOGGING,
    MIDDLEWARE,
    env,
)

DEBUG = True

# In dev we accept any *.localhost host. The "." prefix tells Django to match
# any subdomain, which is exactly what we need for {slug}.mypipelinehero.localhost.
ALLOWED_HOSTS = [".localhost", "127.0.0.1", "0.0.0.0"]

# Cookies can be plaintext over http://*.localhost
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# For cross-subdomain POSTs in dev (the handoff flow hits a tenant subdomain
# from a form on the root domain). "*" is intentionally broad for dev only.
CSRF_TRUSTED_ORIGINS = [
    "http://mypipelinehero.localhost",
    "http://*.mypipelinehero.localhost",
    "http://localhost",
    "http://127.0.0.1",
]

# Email to the console — every dev sees outbound mail in their logs.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Plain-text logs for humans. JSON is harder to read while developing.
LOGGING["handlers"]["console"]["formatter"] = "plain"
LOGGING["root"]["level"] = "DEBUG"

# --- Debug toolbar ---
# Only wired up if debug_toolbar is importable — keeps things working even
# if someone ran `pip install -r requirements/base.txt` instead of dev.txt.
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.common.CommonMiddleware") + 1,
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    )
    # In Docker, the container IP isn't 127.0.0.1, so the default
    # INTERNAL_IPS check doesn't match. This callback always enables the
    # toolbar in dev regardless of client IP.
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }
except ImportError:
    pass

# Optional: turn on SQL query logging when chasing N+1s.
if env.bool("DJANGO_LOG_SQL", default=False):
    LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"
