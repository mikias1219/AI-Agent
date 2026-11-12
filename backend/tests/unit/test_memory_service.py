"""MemoryService propose/confirm and forget-all token."""

from __future__ import annotations

import pytest

from personal_agent.application.services.memory_service import FORGET_CONFIRM_PHRASE, MemoryService
from personal_agent.domain.exceptions import AgentError
from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore


def test_propose_does_not_write(memory_store: SqliteMemoryStore):
    service = MemoryService(memory_store, secret="test")
    proposal = service.propose("preference", "Prefers morning meetings")
    assert proposal["status"] == "proposed"
    assert memory_store.recall("dashboard") == []


def test_create_and_forget_all_with_token(memory_store: SqliteMemoryStore):
    service = MemoryService(memory_store, secret="test")
    service.create("dashboard", "preference", "Prefers morning meetings")
    assert memory_store.recall("dashboard")
    issued = service.issue_forget_token("dashboard")

    with pytest.raises(AgentError):
        service.forget_all("dashboard", token=issued["token"], confirm_phrase="nope")
    deleted = service.forget_all(
        "dashboard",
        token=issued["token"],
        confirm_phrase=FORGET_CONFIRM_PHRASE,
    )
    assert deleted == 1
    assert memory_store.recall("dashboard") == []


def test_redaction_blocks_create(memory_store: SqliteMemoryStore):
    service = MemoryService(memory_store, secret="test")
    with pytest.raises(ValueError):
        service.create("dashboard", "fact", "password: super-secret-value")
