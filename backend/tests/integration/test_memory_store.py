"""Integration: SqliteMemoryStore hybrid recall and permanence."""

from __future__ import annotations

import pytest

from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore


def test_remember_and_recall_roundtrip(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "Prefers concise replies.")
    memory_store.remember("alice", "preference", "Timezone: Europe/Berlin.")

    facts = memory_store.recall("alice")

    assert set(facts) == {"Prefers concise replies.", "Timezone: Europe/Berlin."}


def test_duplicates_are_dropped(memory_store: SqliteMemoryStore):
    first = memory_store.remember("alice", "preference", "Same fact twice.")
    second = memory_store.remember("alice", "preference", "Same fact twice.")

    assert first is not None and second is not None
    assert first.id == second.id
    assert memory_store.recall("alice", kind="preference") == ["Same fact twice."]


def test_kind_filter_and_empty_state(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "Likes tea.")
    memory_store.remember("alice", "fact", "Owns a bicycle.")

    prefs = memory_store.recall("alice", kind="preference")
    assert prefs == ["Likes tea."]
    assert memory_store.recall("nobody") == []


def test_blank_content_is_ignored(memory_store: SqliteMemoryStore):
    with pytest.raises(ValueError):
        memory_store.remember("alice", "preference", "   ")
    assert memory_store.recall("alice") == []


def test_retrieval_limit_is_eight(memory_store: SqliteMemoryStore):
    for i in range(12):
        memory_store.remember("alice", "fact", f"Fact number {i} about scheduling.")
    assert len(memory_store.recall("alice", limit=20)) == 8
    assert len(memory_store.search("alice", "scheduling", limit=20)) == 8


def test_keyword_ranks_relevant_first(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "preference", "Prefers morning meetings")
    memory_store.remember("alice", "fact", "Owns a red bicycle")
    memory_store.remember("alice", "routine", "Runs every evening")

    ranked = memory_store.search("alice", "morning meetings")
    assert ranked
    assert "morning" in ranked[0].content.lower()


def test_delete_is_permanent(memory_store: SqliteMemoryStore):
    memory = memory_store.remember("alice", "fact", "Temporary note")
    assert memory is not None
    memory_store.soft_delete(memory.id)
    assert memory_store.get(memory.id) is None
    assert memory_store.recall("alice") == []


def test_forget_all_removes_everything(memory_store: SqliteMemoryStore):
    memory_store.remember("alice", "fact", "One")
    memory_store.remember("alice", "fact", "Two")
    memory_store.remember("bob", "fact", "Other user")
    assert memory_store.forget_all("alice") == 2
    assert memory_store.recall("alice") == []
    assert memory_store.recall("bob") == ["Other user"]
