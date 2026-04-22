"""
Celery app factory.

Imported by worker and beat containers. Picks up per-app tasks.py modules
via autodiscover_tasks against INSTALLED_APPS.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("mypipelinehero")

# Namespace = "CELERY" means every celery setting in Django settings must be
# prefixed CELERY_ — matches how we already name them in base.py.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Sanity task used during bring-up. Remove in M6 cleanup."""
    print(f"Request: {self.request!r}")
