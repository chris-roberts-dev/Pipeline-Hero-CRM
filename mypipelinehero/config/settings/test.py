"""
Test settings.

Loaded when DJANGO_SETTINGS_MODULE=config.settings.test or via pytest-django's
DJANGO_SETTINGS_MODULE in pytest.ini. Optimized for speed — suites should run
in seconds, not minutes.
"""

from .base import *  # noqa: F401,F403
from .base import REDIS_URL

DEBUG = False

# Any host during tests — RequestFactory and test Client don't care.
ALLOWED_HOSTS = ["*"]

# MD5 password hasher is ~1000x faster than Argon2. Fine for tests, never prod.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# In-memory email — tests inspect mail.outbox.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Local-memory cache — no Redis dependency for unit tests.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    },
}

# Celery tasks run synchronously in tests — no worker needed, no timing races.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Handoff tokens do need Redis (single-use invalidation semantics are hard
# to fake in locmem correctly). Point them at a separate DB so tests don't
# collide with a running dev stack.
HANDOFF_TOKEN_REDIS_URL = f"{REDIS_URL}/15"

# Silence logging during tests unless a test explicitly enables it.
import logging
logging.disable(logging.CRITICAL)
