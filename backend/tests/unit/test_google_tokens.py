"""Sealed Google token round-trip (S6 AES-GCM + v1 migrate)."""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from personal_agent.infrastructure.integrations.google.tokens import (
    V2_PREFIX,
    needs_reseal,
    seal_token,
    unseal_token,
)

SECRET = "test-secret-key-at-least-thirty-two-bytes"


def _seal_v1(secret: str, value: str) -> str:
    key = hashlib.sha256(f"google-oauth-v1:{secret}".encode()).digest()
    raw = value.encode("utf-8")
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    mac = hmac.new(key, xored, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac + xored).decode("ascii")


def test_seal_round_trip():
    sealed = seal_token(SECRET, "ya29.access")
    assert sealed.startswith(V2_PREFIX)
    assert sealed != "ya29.access"
    assert unseal_token(SECRET, sealed) == "ya29.access"
    assert not needs_reseal(sealed)


def test_seal_rejects_tamper():
    sealed = seal_token(SECRET, "tok")
    with pytest.raises(ValueError):
        unseal_token(SECRET, sealed[:-1] + "x")


def test_unseal_legacy_v1_and_needs_reseal():
    v1 = _seal_v1(SECRET, "ya29.legacy")
    assert unseal_token(SECRET, v1) == "ya29.legacy"
    assert needs_reseal(v1)


def test_google_store_saves_sealed_tokens(tmp_path):
    from personal_agent.infrastructure.persistence.database import (
        create_engine_from_url,
        init_db,
        make_session_factory,
    )
    from personal_agent.infrastructure.persistence.google_connection_store import (
        GoogleConnectionStore,
    )

    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'g.db'}")
    init_db(engine)
    store = GoogleConnectionStore(
        make_session_factory(engine),
        secret_key=SECRET,
    )
    store.save_tokens(
        email="user@example.com",
        access_token="access-1",
        refresh_token="refresh-1",
        scopes="email",
    )
    status = store.status(oauth_configured=True)
    assert status["connected"] is True
    assert status["has_tokens"] is True
    assert status["email"] == "user@example.com"
    loaded = store.load_tokens()
    assert loaded["access_token"] == "access-1"
    assert loaded["refresh_token"] == "refresh-1"


def test_google_store_migrates_v1_on_read(tmp_path):
    from personal_agent.infrastructure.persistence.database import (
        create_engine_from_url,
        init_db,
        make_session_factory,
    )
    from personal_agent.infrastructure.persistence.google_connection_store import (
        GoogleConnectionStore,
    )
    from personal_agent.infrastructure.persistence.models import GoogleConnectionRow

    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'g2.db'}")
    init_db(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        session.add(
            GoogleConnectionRow(
                id="default",
                email="legacy@example.com",
                connected=1,
                access_token=_seal_v1(SECRET, "access-v1"),
                refresh_token=_seal_v1(SECRET, "refresh-v1"),
                scopes="email",
            )
        )
        session.commit()

    store = GoogleConnectionStore(factory, secret_key=SECRET)
    loaded = store.load_tokens()
    assert loaded["access_token"] == "access-v1"
    assert loaded["refresh_token"] == "refresh-v1"

    with factory() as session:
        row = session.get(GoogleConnectionRow, "default")
        assert row is not None
        assert row.access_token.startswith(V2_PREFIX)
        assert row.refresh_token.startswith(V2_PREFIX)
        assert not needs_reseal(row.access_token)
