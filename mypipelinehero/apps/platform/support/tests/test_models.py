"""Tests for the ImpersonationSession model."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.platform.organizations.models import Membership, Organization
from apps.platform.support.models import ImpersonationSession

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme")


@pytest.fixture
def support_user(db):
    return User.objects.create_user(email="support@example.com", password="x" * 12)


@pytest.fixture
def target_user(db):
    return User.objects.create_user(email="alice@example.com", password="x" * 12)


@pytest.fixture
def target_membership(db, target_user, org):
    return Membership.objects.create(
        user=target_user, organization=org, status=Membership.Status.ACTIVE
    )


@pytest.fixture
def session_factory(db, support_user, target_user, target_membership, org):
    """Build a fresh ImpersonationSession with sane defaults."""

    def make(**overrides):
        defaults = dict(
            support_user=support_user,
            target_user=target_user,
            target_organization=org,
            target_membership=target_membership,
            reason="Investigating quote acceptance issue per ticket #1234",
            ends_at=timezone.now() + timedelta(minutes=30),
        )
        defaults.update(overrides)
        return ImpersonationSession.objects.create(**defaults)

    return make


@pytest.mark.django_db
class TestSessionId:
    def test_session_id_auto_generated(self, session_factory):
        s = session_factory()
        assert s.session_id
        assert len(s.session_id) >= 30  # token_urlsafe(24) ~ 32 chars

    def test_session_ids_are_unique(self, session_factory):
        s1 = session_factory()
        s2 = session_factory()
        assert s1.session_id != s2.session_id


@pytest.mark.django_db
class TestActiveAndExpired:
    def test_fresh_session_is_active(self, session_factory):
        s = session_factory()
        assert s.is_active is True
        assert s.is_expired is False

    def test_explicitly_ended_is_not_active(self, session_factory):
        s = session_factory()
        s.ended_at = timezone.now()
        s.save()
        assert s.is_active is False
        assert s.is_expired is False  # not "expired" — explicitly ended

    def test_timed_out_is_not_active(self, session_factory):
        s = session_factory(ends_at=timezone.now() - timedelta(minutes=1))
        assert s.is_active is False
        assert s.is_expired is True

    def test_explicitly_ended_takes_precedence_over_expiry(self, session_factory):
        # Edge case: session was both ended_at AND past ends_at. Treat as
        # ended (ended_at is the more specific signal).
        past = timezone.now() - timedelta(minutes=5)
        s = session_factory(ends_at=past)
        s.ended_at = past
        s.save()
        assert s.is_active is False
        assert s.is_expired is False  # not "expired" because ended_at is set


@pytest.mark.django_db
class TestTimeRemaining:
    def test_returns_positive_for_active(self, session_factory):
        s = session_factory(ends_at=timezone.now() + timedelta(minutes=15))
        remaining = s.time_remaining()
        assert remaining.total_seconds() > 0
        assert remaining.total_seconds() < 16 * 60  # not more than 16 min

    def test_returns_negative_for_expired(self, session_factory):
        s = session_factory(ends_at=timezone.now() - timedelta(minutes=5))
        assert s.time_remaining().total_seconds() < 0
