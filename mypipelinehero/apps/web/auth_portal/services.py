"""
Handoff token service.

Cross-subdomain authentication per spec §9.4:

  1. User authenticates on root domain (mypipelinehero.localhost)
  2. User selects an organization (or has exactly one)
  3. Root domain issues a short-lived handoff token for (user, org)
  4. Root domain redirects to https://{slug}.{ROOT_DOMAIN}/auth/handoff?token=...
  5. Tenant subdomain validates the token, invalidates it, establishes a
     tenant-LOCAL session, and the user is in.

Design decisions:
  - **Signed + Redis-backed.** Django's `signing` module provides tamper-
    evident tokens via HMAC. Redis provides single-use semantics and
    short TTL via SETNX + EXPIRE. Either alone is insufficient: signing
    prevents tampering but not replay; Redis prevents replay but not
    tampering if someone guesses the key.
  - **Token format:** opaque URL-safe string. The payload is NOT the
    (user_id, org_id) pair — instead, the signed payload is a random
    identifier ("ticket id"), and Redis stores the mapping of ticket id
    to claim data. This keeps URLs short and prevents user/org IDs from
    leaking into access logs.
  - **60-second max TTL** per spec. Aggressive on purpose — the handoff
    is a redirect chain, not a session cookie, so users never see it.
  - **Single use:** redeeming a token deletes it atomically. Replay
    attempts fail closed.

Token lifecycle:
    issue(user, org) -> token       writes key in Redis, TTL 60s
    redeem(token)   -> claim|None   deletes key, returns claim payload, or
                                    None if token is unknown / expired / replayed

Security threat model:
  - Stolen token within its 60s window: attacker can redeem it once.
    This is the weakest link; mitigations are short TTL and single use.
  - Tampered token: signature check fails, redeem returns None.
  - Replay attempt: Redis key is gone after first redeem, returns None.
  - Infrastructure compromise: if Redis is breached, attacker can forge
    claims. Same blast radius as a database breach — covered by the
    overall security posture, not this layer.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Optional

import redis
from django.conf import settings
from django.core import signing


@dataclass(frozen=True)
class HandoffClaim:
    """The data carried by a valid handoff token.

    Frozen so callers can't mutate fields between validation and use.
    """

    user_id: int
    organization_id: int


# Signer is cheap to construct, but keeping a module-level instance avoids
# the allocation on every token issuance. `salt` namespaces our signatures
# so they can't be confused with other things signed with the same
# SECRET_KEY (e.g., password reset tokens).
_signer = signing.TimestampSigner(salt="mph.handoff.v1")


# Redis key prefix — matches the TTL contract and lets us flush all handoff
# tokens in one pattern-delete if we ever need to invalidate the space.
_KEY_PREFIX = "handoff:ticket:v1:"


def _redis_client():
    """Lazy Redis client factory.

    Lazy so test-suite imports don't fail if Redis isn't reachable, and so
    connection pool lifetime is tied to the worker/web process rather than
    module import. Uses the dedicated handoff-token Redis DB from settings.
    """
    return redis.from_url(settings.HANDOFF_TOKEN_REDIS_URL, decode_responses=True)


def issue(*, user_id: int, organization_id: int) -> str:
    """Issue a single-use handoff token for (user, org).

    Returns an opaque URL-safe string suitable for a query parameter.
    The token is valid for `settings.HANDOFF_TOKEN_TTL_SECONDS` seconds.
    """
    # Random opaque identifier. 32 bytes = 256 bits of entropy, more than
    # enough that brute-forcing within the 60s window is infeasible.
    ticket_id = secrets.token_urlsafe(32)
    key = _KEY_PREFIX + ticket_id

    claim_payload = json.dumps(
        {"user_id": user_id, "organization_id": organization_id}
    )

    client = _redis_client()
    # SETEX in one round-trip: set value with TTL atomically.
    client.setex(key, settings.HANDOFF_TOKEN_TTL_SECONDS, claim_payload)

    # Sign the ticket id so the token can't be forged client-side.
    # TimestampSigner adds its own timestamp which we don't strictly need
    # (Redis TTL already enforces expiry) but the safety-in-depth is cheap.
    return _signer.sign(ticket_id)


def redeem(token: str) -> Optional[HandoffClaim]:
    """Validate and consume a handoff token.

    Returns the claim if the token is valid; returns None for any of:
      - tampered signature
      - expired by signer timestamp (spec: 60s max)
      - already redeemed (single-use — redis key gone)
      - never issued

    This method is designed to be called exactly once per token. The
    claim's Redis entry is deleted atomically on read.
    """
    try:
        ticket_id = _signer.unsign(token, max_age=settings.HANDOFF_TOKEN_TTL_SECONDS)
    except signing.BadSignature:
        return None

    key = _KEY_PREFIX + ticket_id
    client = _redis_client()

    # Atomic "get and delete": GETDEL appeared in Redis 6.2+. Pipelined
    # GET+DELETE is the compatible fallback, but single-use semantics get
    # weaker (race window between GET and DEL). Redis 7 in our compose is
    # fine; using GETDEL.
    payload = client.getdel(key)
    if payload is None:
        return None

    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        # Corrupt payload — treat as invalid. Shouldn't happen since we
        # control the serialization, but fail closed on any surprise.
        return None

    return HandoffClaim(
        user_id=int(data["user_id"]),
        organization_id=int(data["organization_id"]),
    )
