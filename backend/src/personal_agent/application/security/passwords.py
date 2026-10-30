"""Salted password hashing shared by local login and registration."""

import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return "$".join(
        base64.urlsafe_b64encode(value).decode().rstrip("=") for value in (salt, digest)
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        salt_text, expected_text = encoded_hash.split("$", maxsplit=1)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(expected_text + "=" * (-len(expected_text) % 4))
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return hmac.compare_digest(actual, expected)
