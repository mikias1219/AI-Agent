"""Integration: SqliteMemoryStore behavior over a real temp file DB."""

from __future__ import annotations

from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore


def test_remember_and_recall_roundtrip(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "Prefers concise replies.")
    memory_store.remember("alice", "preference", "Timezone: Europe/Berlin.")

    facts = memory_store.recall("alice")

    assert set(facts) == {"Prefers concise replies.", "Timezone: Europe/Berlin."}


def test_duplicates_are_dropped(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "Same fact twice.")
    memory_store.remember("alice", "preference", "Same fact twice.")

    assert memory_store.recall("alice", kind="preference") == ["Same fact twice."]


def test_kind_filter_and_empty_state(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "Likes tea.")
    memory_store.remember("alice", "fact", "Owns a bicycle.")

    prefs = memory_store.recall("alice", kind="preference")
    assert prefs == ["Likes tea."]
    assert memory_store.recall("nobody") == []


def test_blank_content_is_ignored(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "   ")
    assert memory_store.recall("alice") == []
