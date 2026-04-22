"""Shared service-layer utilities.

Domain-specific services live in each domain's own `services.py` module.
This package exports only the cross-cutting shared pieces: base exceptions,
transaction helpers, and outbox event emission (outbox added in M4).
"""

from .exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "PermissionDeniedError",
    "ValidationError",
]
