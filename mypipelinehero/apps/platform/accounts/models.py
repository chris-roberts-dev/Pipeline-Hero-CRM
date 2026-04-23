"""
Custom user model and manager.

Spec §8.1 mandates email as the primary identity and forbids using Django's
default username field. This model MUST be in place before the very first
migration that creates auth tables, because swapping AUTH_USER_MODEL after
data exists is a world of pain.

Design notes:
  - `is_staff` is preserved because Django's admin requires it.
  - `is_superuser` marks platform-level super-admins (spec §7.4). Support users
    who are NOT superusers are modeled separately in M2 via a `SupportProfile`
    or role-based flag — we're deferring that until RBAC lands.
  - No username field. AbstractBaseUser is the minimal base without username;
    PermissionsMixin gives us `is_superuser`, groups, and user_permissions so
    Django's auth backend keeps working the way people expect.
  - We keep `groups` and `user_permissions` even though we're building our own
    RBAC in M2, because the admin and Django's test utilities assume they
    exist. Our RBAC is layered on top, not a replacement.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager for the custom User model.

    Django's built-in UserManager assumes a `username` field, so we have to
    provide our own `create_user` / `create_superuser` that use email instead.
    Both helpers are used by management commands (e.g. `createsuperuser`) and
    by test factories.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Platform user identity.

    A single User may belong to zero, one, or many organizations through
    Membership records (spec §8.2). Users with `is_superuser=True` are global
    platform super-admins who bypass RBAC (spec §10.2 step 1).
    """

    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        help_text=_("Primary identifier. Used for login."),
    )

    # Display-only fields. Kept as plain text with no required format so
    # people can put "Jim" or "Dr. Evelyn Smythe-Robinson III" if they want.
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    # Django admin / auth compatibility flags.
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the Django admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Deactivate instead of deleting accounts to preserve audit history."
        ),
    )

    date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)
    last_login_at = models.DateTimeField(_("last login"), blank=True, null=True)

    objects = UserManager()

    # Django's auth system uses these three class attributes.
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []  # `email` and password are prompted by default

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email
