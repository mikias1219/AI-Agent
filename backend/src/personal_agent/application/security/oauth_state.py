"""Signed, expiring, single-use `state` values for OAuth redirects.

The OAuth callback is reached by a redirect from the identity provider, on a host where
the dashboard session cookie may not exist. The `state` value is therefore the only
proof that the owner started the flow: it is minted behind the login, signed with a
server secret, valid for a few minutes and accepted once.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass

STATE_TTL_SECONDS = 600
_VERSION = "v1"
_CONTEXT = b"compass-oauth-state|"


class OAuthStateError(ValueError):
    """The state value is missing, forged, expired or already used."""


@dataclass(frozen=True, slots=True)
class OAuthState:
    read_only: bool
    nonce: str
    expires_at: int


def _sign(secret: str, payload: str) -> str:
    digest = hmac.new(secret.encode(), _CONTEXT + payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_state(
    secret: str,
    *,
    read_only: bool,
    now: float | None = None,
    ttl_seconds: int = STATE_TTL_SECONDS,
) -> str:
    """Mint a state value. Call only for an authenticated owner."""
    if not secret:
        raise OAuthStateError("No signing secret is configured.")
    issued = time.time() if now is None else now
    expires_at = int(issued) + ttl_seconds
    nonce = secrets.token_urlsafe(18)
    payload = f"{_VERSION}.{1 if read_only else 0}.{expires_at}.{nonce}"
    return f"{payload}.{_sign(secret, payload)}"


def verify_state(secret: str, state: str, *, now: float | None = None) -> OAuthState:
    """Check signature and expiry. Raises OAuthStateError on any problem."""
    if not secret:
        raise OAuthStateError("No signing secret is configured.")
    parts = (state or "").split(".")
    if len(parts) != 5 or parts[0] != _VERSION or parts[1] not in ("0", "1"):
        raise OAuthStateError("Unrecognised state value.")
    version, flag, expires_text, nonce, supplied = parts
    payload = f"{version}.{flag}.{expires_text}.{nonce}"
    if not hmac.compare_digest(_sign(secret, payload), supplied):
        raise OAuthStateError("State signature does not match.")
    try:
        expires_at = int(expires_text)
    except ValueError as exc:
        raise OAuthStateError("Unrecognised state value.") from exc
    current = time.time() if now is None else now
    if current > expires_at:
        raise OAuthStateError("State has expired.")
    return OAuthState(read_only=flag == "1", nonce=nonce, expires_at=expires_at)


class UsedStates:
    """Remembers consumed nonces until they expire, so a state works once.

    Held in process memory: enough for the single API process this product runs as.
    """

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}
        self._lock = threading.Lock()

    def claim(self, state: OAuthState, *, now: float | None = None) -> None:
        """Mark the state as used. Raises OAuthStateError if it was used before."""
        current = time.time() if now is None else now
        with self._lock:
            for nonce in [n for n, expiry in self._seen.items() if expiry < current]:
                del self._seen[nonce]
            if state.nonce in self._seen:
                raise OAuthStateError("State was already used.")
            self._seen[state.nonce] = state.expires_at
