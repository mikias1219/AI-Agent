"""Hub workspace document persists skills / ideas / board notes."""

from personal_agent.infrastructure.persistence.database import (
    create_engine_from_url,
    init_db,
    make_session_factory,
)
from personal_agent.infrastructure.persistence.hub_store import GoogleConnectionStore, HubStore


def test_hub_store_seeds_and_round_trips(tmp_path):
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'hub.db'}")
    init_db(engine)
    store = HubStore(make_session_factory(engine))
    first = store.get_state()
    assert first["skills"]
    assert first["ideas"]
    assert first["boardNotes"]
    first["skills"][0]["status"] = "building"
    saved = store.put_state(first)
    assert saved["skills"][0]["status"] == "building"
    again = store.get_state()
    assert again["skills"][0]["status"] == "building"


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
