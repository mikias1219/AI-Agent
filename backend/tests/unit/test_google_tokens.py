"""Sealed Google token round-trip."""

import pytest

from personal_agent.infrastructure.integrations.google.tokens import seal_token, unseal_token


def test_seal_round_trip():
    sealed = seal_token("test-secret-key-at-least-thirty-two-bytes", "ya29.access")
    assert sealed != "ya29.access"
    assert unseal_token("test-secret-key-at-least-thirty-two-bytes", sealed) == "ya29.access"


def test_seal_rejects_tamper():
    sealed = seal_token("test-secret-key-at-least-thirty-two-bytes", "tok")
    with pytest.raises(ValueError):
        unseal_token("test-secret-key-at-least-thirty-two-bytes", sealed[:-1] + "x")


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
        secret_key="test-secret-key-at-least-thirty-two-bytes",
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
