"""AppConfig for the accounts package."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.platform.accounts"
    # `label` is what appears in AUTH_USER_MODEL. Must match the value we set
    # in settings/base.py: AUTH_USER_MODEL = "accounts.User".
    label = "accounts"
    verbose_name = "Accounts"
