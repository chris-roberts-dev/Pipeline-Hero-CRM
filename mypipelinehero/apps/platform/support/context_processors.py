"""
Context processor: expose impersonation state to every template.

Templates can read the resulting `impersonation` context variable to
render the banner — see `templates/support/_banner.html`. When no
impersonation is active, the value is None and the banner template is
a no-op.

Wired up in TEMPLATES.OPTIONS.context_processors in config/settings/base.py.
"""

from __future__ import annotations

from typing import Any


def impersonation(request) -> dict[str, Any]:
    """Return `{'impersonation': <session-or-none>}` for templates.

    The middleware attaches `request.impersonation_session` (None or an
    active session). We just expose it under a friendlier name. No DB
    queries here — the heavy work happened once in the middleware.
    """
    return {
        "impersonation": getattr(request, "impersonation_session", None),
    }
