"""
Top-level pytest configuration.

pytest-django picks up DJANGO_SETTINGS_MODULE from pyproject.toml's
[tool.pytest.ini_options] so there's nothing to do here beyond marking
this directory as the test root. Per-app conftest.py files handle
app-specific fixtures.
"""
