"""Tests for the handoff token service (issue / redeem / single-use)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from freezegun import freeze_time

from apps.web.auth_portal.services import HandoffClaim, issue, redeem


@pytest.fixture(autouse=True)
def _clear_handoff_redis():
    """Each test starts with an empty handoff-token Redis DB."""
    import redis as redis_lib
    from django.conf import settings

    client = redis_lib.from_url(settings.HANDOFF_TOKEN_REDIS_URL, decode_responses=True)
    client.flushdb()
    yield
    client.flushdb()


class TestIssueAndRedeem:
    def test_issue_returns_nonempty_string(self) -> None:
        token = issue(user_id=1, organization_id=2)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_redeem_valid_token_returns_claim(self) -> None:
        token = issue(user_id=42, organization_id=7)
        claim = redeem(token)
        assert claim == HandoffClaim(user_id=42, organization_id=7)

    def test_redeem_is_single_use(self) -> None:
        # Second redemption must fail — this is the core replay-prevention
        # property per spec §9.4.
        token = issue(user_id=1, organization_id=1)
        first = redeem(token)
        assert first is not None
        second = redeem(token)
        assert second is None

    def test_redeem_unknown_token_returns_none(self) -> None:
        # Well-formed signed token referencing a ticket that was never
        # issued (or was already redeemed and garbage-collected).
        from django.core.signing import TimestampSigner

        signer = TimestampSigner(salt="mph.handoff.v1")
        fake = signer.sign("not-a-real-ticket")
        assert redeem(fake) is None

    def test_redeem_tampered_token_returns_none(self) -> None:
        token = issue(user_id=1, organization_id=1)
        # Flip a character — signature check must fail.
        tampered = token[:-3] + ("A" if token[-3] != "A" else "B") + token[-2:]
        assert redeem(tampered) is None

    def test_redeem_malformed_token_returns_none(self) -> None:
        assert redeem("not-a-token") is None
        assert redeem("") is None

    def test_redeem_expired_token_returns_none(self) -> None:
        # Spec §9.4: max 60-second lifetime. Freeze time, issue, jump 70s, redeem.
        with freeze_time("2026-01-01 12:00:00") as frozen:
            token = issue(user_id=1, organization_id=1)
            frozen.move_to("2026-01-01 12:01:10")  # +70s
            assert redeem(token) is None

    def test_two_separate_tokens_are_independent(self) -> None:
        t1 = issue(user_id=1, organization_id=1)
        t2 = issue(user_id=2, organization_id=2)

        c1 = redeem(t1)
        assert c1 == HandoffClaim(user_id=1, organization_id=1)

        # Redeeming t1 must NOT invalidate t2.
        c2 = redeem(t2)
        assert c2 == HandoffClaim(user_id=2, organization_id=2)
