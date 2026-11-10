"""Seal Google OAuth tokens at rest using a key derived from the dashboard secret."""

from __future__ import annotations

import base64
import hashlib
import hmac


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(f"google-oauth-v1:{secret}".encode()).digest()


def seal_token(secret: str, value: str) -> str:
    if not value:
        return ""
    if not secret:
        raise ValueError("Cannot seal Google tokens without DASHBOARD_SECRET_KEY.")
    key = _derive_key(secret)
    raw = value.encode("utf-8")
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    mac = hmac.new(key, xored, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac + xored).decode("ascii")


def unseal_token(secret: str, sealed: str) -> str:
    if not sealed:
        return ""
    if not secret:
        raise ValueError("Cannot unseal Google tokens without DASHBOARD_SECRET_KEY.")
    key = _derive_key(secret)
    try:
        blob = base64.urlsafe_b64decode(sealed.encode("ascii"))
    except Exception as exc:  # noqa: BLE001 — treat any decode failure as invalid seal
        raise ValueError("Invalid sealed Google token.") from exc
    if len(blob) < 32:
        raise ValueError("Invalid sealed Google token.")
    mac, xored = blob[:32], blob[32:]
    expected = hmac.new(key, xored, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("Google token seal MAC mismatch.")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(xored)).decode("utf-8")
