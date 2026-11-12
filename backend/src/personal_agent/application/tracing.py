"""Application-level trace id helpers (OBS-02).

Concrete exporters live in infrastructure; this module stays importable from
application without crossing into adapters.
"""

from __future__ import annotations

import secrets


def new_trace_id() -> str:
    """Return a W3C-like 32-character lowercase hex trace id."""
    return secrets.token_hex(16)
