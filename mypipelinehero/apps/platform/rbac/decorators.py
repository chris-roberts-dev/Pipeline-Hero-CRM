"""
View-layer permission decorators.

`@require_capability(code)` is the standard gate for views that require a
specific capability. `@no_capability_required` marks views that legitimately
have no capability gate (login, public landing, healthchecks).

The capability-coverage CI test walks every URL pattern and asserts each
view has one or the other. A view with neither is a bug — it's either a
forgotten gate (security risk) or an intentional opt-out that should be
explicit (so it's reviewable).

Usage:

    @require_capability("quotes.approve")
    def approve_quote(request, quote_id):
        ...

    @no_capability_required(reason="Public landing page; pre-auth.")
    def landing(request):
        ...

The decorator depends on `request.acting_membership` being set (typically
by TenancyMiddleware once that's wired). If the attribute is missing, the
decorator denies — "implicit allow" is forbidden.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from django.http import HttpRequest

from apps.common.services.exceptions import PermissionDeniedError
from apps.platform.rbac.evaluator import has_capability


# Marker attributes attached to view functions. The coverage test reads
# these — picking distinctive names so they don't collide with anything
# Django itself sets.
_REQUIRED_CAP_ATTR = "_rbac_required_capability"
_OPT_OUT_ATTR = "_rbac_no_capability_required"


def require_capability(capability_code: str) -> Callable:
    """Decorator that requires the request's acting membership to hold
    `capability_code`. Raises PermissionDeniedError if not.

    Args:
        capability_code: A capability code string. Not validated against
            the registry at decoration time — typos surface in tests.

    Marks the view with `_rbac_required_capability` so the coverage test
    can verify every URL has a capability declaration.
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs):
            user = getattr(request, "user", None)
            membership = getattr(request, "acting_membership", None)

            if not has_capability(
                user=user,
                membership=membership,
                capability_code=capability_code,
                request=request,
            ):
                # Service-layer-style domain exception. The view dispatcher
                # / middleware translates this to HTTP 403. Keeping the
                # exception type consistent with service-layer denials
                # means a single exception handler covers both cases.
                raise PermissionDeniedError(
                    f"Capability '{capability_code}' is required."
                )
            return view_func(request, *args, **kwargs)

        # Mark for the coverage test.
        setattr(wrapped, _REQUIRED_CAP_ATTR, capability_code)
        return wrapped

    return decorator


def no_capability_required(*, reason: str) -> Callable:
    """Explicit opt-out marker for views that legitimately need no capability gate.

    Examples: login, public landing, healthcheck, error pages.

    The `reason` is mandatory — it's there so a code reviewer can decide
    whether the opt-out is justified without git-blame-archaeology.

    Args:
        reason: Why this view doesn't require a capability. Stored on the
            view for future audit / introspection.
    """
    if not reason:
        raise ValueError("no_capability_required requires a non-empty reason.")

    def decorator(view_func: Callable) -> Callable:
        # No wrapping needed — this decorator only sets the marker.
        # Wrapping would be wasted overhead since we're not gating.
        setattr(view_func, _OPT_OUT_ATTR, reason)
        return view_func

    return decorator


# ---------------------------------------------------------------------------
# Helpers used by the coverage test (and potentially by introspection tooling)
# ---------------------------------------------------------------------------


def get_required_capability(view_func: Callable) -> str | None:
    """Return the capability declared by @require_capability, or None.

    Walks `__wrapped__` / `__func__` so it works with method-based views
    where the decorator is applied to an instance method.
    """
    target = view_func
    # Drill through wrappers — class-based views, partials, etc.
    for _ in range(8):
        if hasattr(target, _REQUIRED_CAP_ATTR):
            return getattr(target, _REQUIRED_CAP_ATTR)
        target = getattr(target, "__wrapped__", None) or getattr(target, "view_class", None)
        if target is None:
            return None
    return None


def is_capability_exempt(view_func: Callable) -> bool:
    """Return True if the view declared @no_capability_required."""
    target = view_func
    for _ in range(8):
        if hasattr(target, _OPT_OUT_ATTR):
            return True
        target = getattr(target, "__wrapped__", None) or getattr(target, "view_class", None)
        if target is None:
            return False
    return False
