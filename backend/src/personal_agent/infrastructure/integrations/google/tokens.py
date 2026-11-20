"""Seal Google OAuth tokens at rest (S6).

v2: AES-256-GCM with a key derived from DASHBOARD_SECRET_KEY (authenticated encryption).
v1: legacy XOR+HMAC — still readable so tokens migrate on the next save.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

V2_PREFIX = "v2gcm:"
_V1_LABEL = "google-oauth-v1"
_V2_LABEL = "google-oauth-v2"


def _derive_key(secret: str, *, label: str) -> bytes:
    return hashlib.sha256(f"{label}:{secret}".encode()).digest()


def seal_token(secret: str, value: str) -> str:
    if not value:
        return ""
    if not secret:
        raise ValueError("Cannot seal Google tokens without DASHBOARD_SECRET_KEY.")
    key = _derive_key(secret, label=_V2_LABEL)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode("utf-8"), None)
    blob = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{V2_PREFIX}{blob}"


def unseal_token(secret: str, sealed: str) -> str:
    if not sealed:
        return ""
    if not secret:
        raise ValueError("Cannot unseal Google tokens without DASHBOARD_SECRET_KEY.")
    if sealed.startswith(V2_PREFIX):
        return _unseal_v2(secret, sealed[len(V2_PREFIX) :])
    return _unseal_v1(secret, sealed)


def needs_reseal(sealed: str) -> bool:
    """True when the stored blob is legacy v1 and should be rewritten as v2."""
    return bool(sealed) and not sealed.startswith(V2_PREFIX)


def _unseal_v2(secret: str, blob_b64: str) -> str:
    key = _derive_key(secret, label=_V2_LABEL)
    try:
        blob = base64.urlsafe_b64decode(blob_b64.encode("ascii"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid sealed Google token.") from exc
    if len(blob) < 13:
        raise ValueError("Invalid sealed Google token.")
    nonce, ciphertext = blob[:12], blob[12:]
    try:
        plain = AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as exc:  # noqa: BLE001 — AEAD failure
        raise ValueError("Google token seal authentication failed.") from exc
    return plain.decode("utf-8")


def _unseal_v1(secret: str, sealed: str) -> str:
    """Legacy XOR+HMAC (pre-S6). Kept for migrate-on-read."""
    key = _derive_key(secret, label=_V1_LABEL)
    try:
        blob = base64.urlsafe_b64decode(sealed.encode("ascii"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid sealed Google token.") from exc
    if len(blob) < 32:
        raise ValueError("Invalid sealed Google token.")
    mac, xored = blob[:32], blob[32:]
    expected = hmac.new(key, xored, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("Google token seal MAC mismatch.")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(xored)).decode("utf-8")
