"""
ASGI config. Not used in Phase 1 but present so async views / channels can
be adopted later without another scaffolding round.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_asgi_application()
