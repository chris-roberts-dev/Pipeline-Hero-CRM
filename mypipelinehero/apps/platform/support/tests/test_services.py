"""Tests for apps.platform.support.services."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.common.services import PermissionDeniedError, ValidationError
from apps.platform.audit.models import AuditEvent
from apps.platform.organizations.models import Membership, Organization
from apps.platform.support.models import ImpersonationSession
from apps.platform.support.services import (
    end_impersonation,
    get_active_session,
    start_impersonation,
)

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="root@example.com", password="x" * 12)


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email="alice@example.com", password="x" * 12)


@pytest.fixture
def regular_user_member(db, regular_user, org):
    return Membership.objects.create(
        user=regular_user, organization=org, status=Membership.Status.ACTIVE
    )


# ---------------------------------------------------------------------------
# start_impersonation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStartImpersonation:
    def test_superuser_can_start(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating quote acceptance issue per ticket #1234",
        )
        assert session.pk is not None
        assert session.support_user == superuser
        assert session.target_user == regular_user
        assert session.target_membership == regular_user_member
        assert session.is_active

    def test_non_superuser_without_capability_rejected(
        self, regular_user, org, regular_user_member
    ):
        # A second regular user attempting to impersonate without
        # holding support.impersonation.start.
        attacker = User.objects.create_user(
            email="attacker@example.com", password="x" * 12
        )
        with pytest.raises(PermissionDeniedError):
            start_impersonation(
                support_user=attacker,
                target_user=regular_user,
                target_organization=org,
                reason="Trying to impersonate without authorization",
            )

    def test_short_reason_rejected(
        self, superuser, regular_user, regular_user_member, org
    ):
        with pytest.raises(ValidationError, match="meaningful reason"):
            start_impersonation(
                support_user=superuser,
                target_user=regular_user,
                target_organization=org,
                reason="x",
            )

    def test_empty_reason_rejected(
        self, superuser, regular_user, regular_user_member, org
    ):
        with pytest.raises(ValidationError):
            start_impersonation(
                support_user=superuser,
                target_user=regular_user,
                target_organization=org,
                reason="",
            )

    def test_whitespace_only_reason_rejected(
        self, superuser, regular_user, regular_user_member, org
    ):
        with pytest.raises(ValidationError):
            start_impersonation(
                support_user=superuser,
                target_user=regular_user,
                target_organization=org,
                reason="          ",
            )

    def test_target_without_membership_rejected(self, superuser, regular_user, org):
        # No membership for regular_user yet.
        with pytest.raises(ValidationError, match="active membership"):
            start_impersonation(
                support_user=superuser,
                target_user=regular_user,
                target_organization=org,
                reason="Investigating an issue per ticket #1234",
            )

    def test_target_with_only_suspended_membership_rejected(
        self, superuser, regular_user, org
    ):
        Membership.objects.create(
            user=regular_user, organization=org, status=Membership.Status.SUSPENDED
        )
        with pytest.raises(ValidationError, match="active membership"):
            start_impersonation(
                support_user=superuser,
                target_user=regular_user,
                target_organization=org,
                reason="Investigating an issue per ticket #1234",
            )

    def test_self_impersonation_rejected(self, superuser):
        # The superuser tries to impersonate themselves.
        with pytest.raises(ValidationError, match="yourself"):
            start_impersonation(
                support_user=superuser,
                target_user=superuser,
                target_organization=Organization.objects.create(name="X", slug="x"),
                reason="Trying to impersonate myself, somehow",
            )

    def test_cannot_impersonate_another_superuser(self, superuser, org):
        another_super = User.objects.create_superuser(
            email="root2@example.com", password="x" * 12
        )
        Membership.objects.create(
            user=another_super, organization=org, status=Membership.Status.ACTIVE
        )
        with pytest.raises(ValidationError, match="superuser"):
            start_impersonation(
                support_user=superuser,
                target_user=another_super,
                target_organization=org,
                reason="Trying to impersonate another superuser",
            )

    def test_emits_impersonation_started_audit_event(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating quote acceptance issue per ticket #1234",
        )
        evt = AuditEvent.objects.get(event_type="IMPERSONATION_STARTED")
        assert evt.actor_user == superuser
        assert evt.organization == org
        # The on_behalf_of is None for the start event itself —
        # impersonation isn't "active" until after start completes.
        assert evt.on_behalf_of_user is None
        assert evt.metadata["session_id"] == session.session_id
        assert evt.metadata["target_user_id"] == regular_user.pk

    def test_session_ttl_uses_settings(
        self, settings, superuser, regular_user, regular_user_member, org
    ):
        settings.IMPERSONATION_TTL_MINUTES = 5
        before = timezone.now()
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating quote acceptance issue per ticket #1234",
        )
        elapsed = session.ends_at - before
        # 5 minutes ± a small buffer for execution.
        assert (
            timedelta(minutes=4, seconds=55)
            <= elapsed
            <= timedelta(minutes=5, seconds=5)
        )


# ---------------------------------------------------------------------------
# end_impersonation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEndImpersonation:
    def test_self_end_succeeds(self, superuser, regular_user, regular_user_member, org):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        end_impersonation(session=session, ending_user=superuser)
        session.refresh_from_db()
        assert session.ended_at is not None
        assert session.ended_by == superuser
        assert session.end_reason == "self_end"
        assert not session.is_active

    def test_already_ended_rejected(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        end_impersonation(session=session, ending_user=superuser)
        with pytest.raises(ValidationError, match="already ended"):
            end_impersonation(session=session, ending_user=superuser)

    def test_force_end_without_capability_rejected(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        # A different non-superuser tries to force-end.
        other_admin = User.objects.create_user(
            email="other@example.com", password="x" * 12
        )
        with pytest.raises(PermissionDeniedError, match="end_any"):
            end_impersonation(session=session, ending_user=other_admin)
        # Session is still active.
        session.refresh_from_db()
        assert session.is_active

    def test_force_end_by_another_superuser_succeeds(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        # Another superuser force-ends. Superuser has end_any via
        # evaluator step 1 short-circuit.
        forcer = User.objects.create_superuser(
            email="forcer@example.com", password="x" * 12
        )
        end_impersonation(
            session=session, ending_user=forcer, end_reason="security_concern"
        )
        session.refresh_from_db()
        assert session.ended_by == forcer
        assert session.end_reason == "security_concern"

    def test_emits_impersonation_ended_audit_event(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        # Clear the START event so we can isolate the END event check.
        AuditEvent.objects.filter(event_type="IMPERSONATION_STARTED").delete()

        end_impersonation(session=session, ending_user=superuser)

        evt = AuditEvent.objects.get(event_type="IMPERSONATION_ENDED")
        assert evt.actor_user == superuser
        assert evt.organization == org
        assert evt.metadata["session_id"] == session.session_id
        assert evt.metadata["is_self_end"] is True
        assert "duration_seconds" in evt.metadata


# ---------------------------------------------------------------------------
# get_active_session
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetActiveSession:
    def test_returns_active_session(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        result = get_active_session(session.session_id)
        assert result is not None
        assert result.pk == session.pk

    def test_returns_none_for_unknown_session_id(self):
        assert get_active_session("not-a-real-session-id") is None

    def test_returns_none_for_empty_session_id(self):
        assert get_active_session("") is None
        assert get_active_session(None) is None

    def test_returns_none_for_ended_session(
        self, superuser, regular_user, regular_user_member, org
    ):
        session = start_impersonation(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            reason="Investigating an issue per ticket #1234",
        )
        end_impersonation(session=session, ending_user=superuser)
        assert get_active_session(session.session_id) is None

    def test_returns_none_for_expired_session(
        self, superuser, regular_user, regular_user_member, org
    ):
        # Manually create an expired session to avoid clock-mocking.
        expired = ImpersonationSession.objects.create(
            support_user=superuser,
            target_user=regular_user,
            target_organization=org,
            target_membership=regular_user_member,
            reason="An expired session for testing",
            ends_at=timezone.now() - timedelta(minutes=1),
        )
        assert get_active_session(expired.session_id) is None
