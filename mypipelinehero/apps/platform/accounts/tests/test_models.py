"""Smoke tests for the custom User model."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user_with_email(self) -> None:
        user = User.objects.create_user(email="jim@example.com", password="correct horse battery")
        assert user.email == "jim@example.com"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("correct horse battery")

    def test_create_user_normalizes_email_domain(self) -> None:
        # BaseUserManager.normalize_email lowercases the domain, not the local part.
        user = User.objects.create_user(email="Jim@EXAMPLE.COM", password="x" * 12)
        assert user.email == "Jim@example.com"

    def test_create_user_requires_email(self) -> None:
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="x" * 12)

    def test_create_superuser_flags_correct(self) -> None:
        su = User.objects.create_superuser(email="boss@example.com", password="x" * 12)
        assert su.is_staff is True
        assert su.is_superuser is True

    def test_email_is_unique(self) -> None:
        User.objects.create_user(email="dup@example.com", password="x" * 12)
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            User.objects.create_user(email="dup@example.com", password="x" * 12)

    def test_username_field_is_email(self) -> None:
        # Regression guard: if someone "helpfully" adds a username field,
        # this test catches it.
        assert User.USERNAME_FIELD == "email"

    def test_str_returns_email(self) -> None:
        user = User(email="whoami@example.com")
        assert str(user) == "whoami@example.com"

    def test_get_full_name_falls_back_to_email(self) -> None:
        user = User(email="noname@example.com")
        assert user.get_full_name() == "noname@example.com"

        user.first_name = "Jim"
        user.last_name = "Kirk"
        assert user.get_full_name() == "Jim Kirk"
