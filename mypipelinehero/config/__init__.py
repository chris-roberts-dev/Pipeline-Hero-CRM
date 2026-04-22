"""
Root Django project package.

Importing the Celery app here guarantees it's registered whenever Django
starts — so shared_task decorators elsewhere find the right app instance.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
