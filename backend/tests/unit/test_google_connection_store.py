"""Google connection store persistence."""

from personal_agent.infrastructure.persistence.database import (
    create_engine_from_url,
    init_db,
    make_session_factory,
)
from personal_agent.infrastructure.persistence.google_connection_store import GoogleConnectionStore


def test_google_connection_status(tmp_path):
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'g.db'}")
    init_db(engine)
    store = GoogleConnectionStore(make_session_factory(engine))
    assert store.status(oauth_configured=False)["connected"] is False
    store.mark_connected("a@b.com")
    assert store.status(oauth_configured=True)["connected"] is True
    assert store.status(oauth_configured=True)["email"] == "a@b.com"
    store.disconnect()
    assert store.status(oauth_configured=True)["connected"] is False
