"""
Capability coverage CI test.

Every routed view in the application must declare either:
  - @require_capability("some.cap") to gate access by capability, OR
  - @no_capability_required(reason="...") to explicitly opt out

A view with neither is a bug. It's either a forgotten gate (silent
permission bypass — security risk) or an intentional public endpoint that
wasn't documented (so a reviewer can't tell which).

This test walks BOTH URLconfs (root domain and tenant subdomain), enumerates
every view callable, and asserts each carries one marker or the other.

Adding this test to the CI surface makes "I forgot to think about access
control on my new view" a build failure rather than a production CVE.
"""

from __future__ import annotations

import importlib

from django.urls import URLPattern, URLResolver, get_resolver

from apps.platform.rbac.decorators import (
    get_required_capability,
    is_capability_exempt,
)


# Both URLconf modules need walking. Adding a new dispatch tree requires
# adding it here; that's intentional friction — new dispatch trees are
# rare events that warrant explicit acknowledgement.
URLCONFS_TO_CHECK = [
    "config.urls",          # root-domain URLconf
    "config.urls_tenant",   # tenant-subdomain URLconf
]


def _walk(patterns, prefix: str = ""):
    """Yield (route_path, callback) for every leaf URL pattern.

    Recurses into URLResolver (for `include()`d URL trees). Includes the
    full path prefix in the route for debugging — when the test fails,
    you want to see exactly which URL is unmarked.
    """
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry.callback


# Some views are technically routed but are NOT user-facing — debug toolbar's
# panel routes, Django's static file serving in dev, etc. The coverage test
# isn't responsible for these. Match on the dotted path of the view function.
_THIRD_PARTY_VIEW_PREFIXES = (
    "debug_toolbar.",
    "django.views.",
    "django.contrib.",
    "django_extensions.",
)


def _is_third_party_view(callback) -> bool:
    """True if the callback comes from a third-party package we don't
    own and shouldn't be policing for capability markers."""
    module = getattr(callback, "__module__", "") or ""
    return any(module.startswith(prefix) for prefix in _THIRD_PARTY_VIEW_PREFIXES)


def test_every_view_declares_a_capability_marker():
    """Walks every routed view and confirms the marker is present.

    The error message lists ALL offending views in one go so a developer
    can fix them in a single batch rather than playing whack-a-mole.
    """
    unmarked: list[str] = []

    for urlconf in URLCONFS_TO_CHECK:
        module = importlib.import_module(urlconf)
        resolver = get_resolver(urlconf)

        for path_str, callback in _walk(resolver.url_patterns):
            if _is_third_party_view(callback):
                continue

            has_required = get_required_capability(callback) is not None
            has_opt_out = is_capability_exempt(callback)

            if not (has_required or has_opt_out):
                # Use __qualname__ when available; falls back to repr for
                # functools.partial and other oddities.
                view_id = getattr(
                    callback, "__qualname__", repr(callback)
                )
                view_module = getattr(callback, "__module__", "?")
                unmarked.append(
                    f"  {urlconf} :: {path_str!r} → {view_module}.{view_id}"
                )

    assert not unmarked, (
        "The following views have no capability marker. Each must declare "
        "either @require_capability(...) or @no_capability_required(reason=...). "
        "If a view is genuinely public, use @no_capability_required with a "
        "clear reason — explicit opt-out is required.\n\n"
        + "\n".join(unmarked)
    )
