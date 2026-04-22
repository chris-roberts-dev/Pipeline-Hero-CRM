"""
WSGI config. The actual settings module is chosen via DJANGO_SETTINGS_MODULE.
Do NOT hardcode a default here — in prod we want a loud failure if the env
var is missing rather than a silent fallback to dev.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()
