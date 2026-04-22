"""
Typed domain exceptions.

Services raise these; views translate them to HTTP responses. This keeps
business logic free of HTTP concerns and makes services callable from any
context (views, Celery tasks, management commands, Phase 2 API).

Naming convention: every exception extends `DomainError`. Domain-specific
subclasses live in the domain's own exceptions module (e.g.
apps.platform.accounts.exceptions for auth-specific ones) and extend the
generic ones here.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all service-layer errors.

    Views catch DomainError subclasses at the boundary and render the
    appropriate response (400, 403, 404, etc.). Unhandled exceptions bubble
    up as 500s — which is what we want for genuinely unexpected failures.
    """


class ValidationError(DomainError):
    """The inputs violated a domain rule (not a DB or field-level validation).

    Use this for things like "cannot accept a quote that's already declined"
    — business-rule violations that aren't well-formed field problems.
    """


class NotFoundError(DomainError):
    """The requested record doesn't exist, or isn't visible to this caller.

    Prefer this over raising Django's Model.DoesNotExist — it keeps the
    abstraction clean and avoids leaking ORM specifics to callers.
    """


class PermissionDeniedError(DomainError):
    """The caller lacks permission for this action.

    Authorization failure at the domain layer (capability missing, org
    mismatch, object not in permitted scope). Distinct from authentication
    failures, which are their own subclass.
    """


class AuthenticationError(DomainError):
    """The caller could not be authenticated.

    Used for login failures, expired tokens, invalid credentials. Distinct
    from PermissionDeniedError, which assumes authenticated-but-not-allowed.
    """


class ConflictError(DomainError):
    """The operation conflicts with current state.

    Use for optimistic concurrency mismatches, duplicate-submission, or
    state-machine transition conflicts ("this quote was already accepted").
    """
