"""
Base settings shared across all environments.

Every environment-specific file (dev.py, test.py, prod.py) imports from this.
Everything configurable lives in environment variables — see .env.example for
the full list. Code-level defaults are chosen for safety, not convenience.
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# BASE_DIR points at the repo root (the directory containing manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------
# Reads .env from the repo root. Missing keys raise at access time, not import
# time — so a settings file that reads an unset key will fail fast with a clear
# error, not a mysterious empty-string default.
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

# ALLOWED_HOSTS is a comma-separated list. In dev it'll include
# `.localhost` for wildcard tenant subdomain support.
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Root domain that serves the login landing page. Tenant portals live at
# {slug}.{ROOT_DOMAIN}. Used by the cross-subdomain handoff flow (M1).
ROOT_DOMAIN = env("MPH_ROOT_DOMAIN", default="mypipelinehero.localhost")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # django.contrib.admin is added later once the custom AdminSite lands in M2.
    # Keeping the default admin out of INSTALLED_APPS until then prevents
    # accidental "just use the default admin" paths from sneaking in.
]

THIRD_PARTY_APPS = [
    "django_celery_beat",
]

# Local apps are listed by domain area matching the repo layout.
# Every app is currently an empty placeholder — models and admin follow in
# later milestones. Listed here so Django picks them up as soon as they have
# models or migrations.
LOCAL_APPS = [
    # Platform / identity
    "apps.platform.accounts",
    "apps.platform.organizations",
    "apps.platform.rbac",
    "apps.platform.audit",
    "apps.platform.support",
    # Web surfaces
    "apps.web.landing",
    "apps.web.auth_portal",
    "apps.web.tenant_portal",
    # CRM domains
    "apps.crm.leads",
    "apps.crm.quotes",
    "apps.crm.clients",
    "apps.crm.tasks",
    "apps.crm.communications",
    "apps.crm.orders",
    "apps.crm.billing",
    # Files / reporting
    "apps.files.attachments",
    "apps.reporting.exports",
    # Catalog
    "apps.catalog.services",
    "apps.catalog.products",
    "apps.catalog.materials",
    "apps.catalog.suppliers",
    "apps.catalog.pricing",
    "apps.catalog.manufacturing",
    # Operations
    "apps.operations.locations",
    "apps.operations.purchasing",
    "apps.operations.build",
    "apps.operations.workorders",
    # Shared
    "apps.common.tenancy",
    "apps.common.outbox",
    # apps.api is Phase 2 — intentionally NOT installed in Phase 1.
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# TenancyMiddleware resolves {slug}.{ROOT_DOMAIN} -> request.organization.
# Placed after AuthenticationMiddleware because some downstream authorization
# logic wants both user AND organization in a single check.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.common.tenancy.middleware.TenancyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# DATABASE_URL drives connection. In prod this points at pgBouncer, not at
# Postgres directly. See docker-compose and prod runbook.
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgres://mph:mph@postgres:5432/mph",
    ),
}
# Persistent DB connections. 0 = reopen per request (safe default).
# Tuned up in prod settings where pgBouncer handles pooling.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DJANGO_CONN_MAX_AGE", default=0)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
# Custom user model per spec §8.1. The `accounts` label is defined by
# apps.platform.accounts.apps.AccountsConfig. Swapping this value after data
# exists is essentially a rebuild, so it's set from the first migration baseline.
AUTH_USER_MODEL = "accounts.User"

# Argon2 first (installed via argon2-cffi); Django falls back on the others
# for rehashing legacy passwords if any ever exist.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Auth redirects
# ---------------------------------------------------------------------------
# @login_required and friends redirect here when auth is required. Name-based
# so we can move the URL later without touching settings.
LOGIN_URL = "landing:login"
LOGIN_REDIRECT_URL = "landing:login"  # post-login routing is handled by the
                                      # login view itself (see services).

# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
# DB-backed sessions are the default and fine for now.
# Cross-subdomain session note: we do NOT use a shared parent-domain cookie.
# Each subdomain ({slug}.mypipelinehero.com and the root) gets its own
# session cookie. SESSION_COOKIE_DOMAIN is intentionally left unset so the
# cookie is scoped to the exact host the response came from. This is
# spec §9.4 — the handoff token is what crosses the subdomain boundary,
# not the cookie.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
CSRF_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# i18n / tz
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"           # Always store UTC; render per-user tz in templates
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"      # collectstatic target
STATICFILES_DIRS = [BASE_DIR / "static"]    # source dirs

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default storage backend — overridden in prod to point at S3-compatible
# object storage per spec §24.6.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Cache + Celery + Redis
# ---------------------------------------------------------------------------
# Redis is one service, multiple logical DBs:
#   db 0 - cache
#   db 1 - celery broker
#   db 2 - celery result backend
#   db 3 - handoff tokens + other short-lived signed artifacts (M1)
REDIS_URL = env("REDIS_URL", default="redis://redis:6379")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/0",
    },
}

CELERY_BROKER_URL = f"{REDIS_URL}/1"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/2"
CELERY_TASK_ACKS_LATE = True                # Requeue if worker dies mid-task
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1       # Fair dispatch; matters for slow tasks
CELERY_TASK_TIME_LIMIT = 600                # Hard 10-min ceiling
CELERY_TASK_SOFT_TIME_LIMIT = 540           # Soft 9-min so tasks can clean up
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

HANDOFF_TOKEN_REDIS_URL = f"{REDIS_URL}/3"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Dev overrides this to the console backend. Prod picks a real provider.
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", default="noreply@mypipelinehero.localhost")
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Structured JSON logs per spec §28. Dev settings override to plain text for
# readability; prod and worker containers emit JSON for log aggregation.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "plain": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django.db.backends": {      # SQL queries — off by default, dev flips on
            "level": "WARNING",
            "propagate": True,
        },
    },
}

# ---------------------------------------------------------------------------
# MyPipelineHero-specific
# ---------------------------------------------------------------------------
# Handoff token lifetime — spec §9.4 says max 60s.
HANDOFF_TOKEN_TTL_SECONDS = 60

# Org slug cache TTL. Short enough that a slug/status change propagates fast
# even before explicit invalidation; long enough to cut request-path DB hits.
ORG_SLUG_CACHE_TTL_SECONDS = 300
