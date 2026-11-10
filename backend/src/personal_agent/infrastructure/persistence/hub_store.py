"""Personal Agent Hub workspace document (skills / ideas / board notes)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import sessionmaker

from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import GoogleConnectionRow, HubWorkspaceRow

DEFAULT_HUB: dict[str, Any] = {
    "skills": [
        {
            "id": "sk-tg-draft",
            "channelId": "telegram",
            "capabilityId": "cap-tg-replies",
            "name": "Draft Telegram reply",
            "status": "live",
            "humanControl": "You approve before any send.",
            "deliverables": "Suggested reply text in chat.",
        },
        {
            "id": "sk-tg-bot",
            "channelId": "telegram",
            "capabilityId": "cap-tg-inbox",
            "name": "Bot runtime control",
            "status": "live",
            "humanControl": "Start/stop from the hub only.",
            "deliverables": "Bot listening state.",
        },
        {
            "id": "sk-gm-summary",
            "channelId": "gmail",
            "capabilityId": "cap-gm-inbox",
            "name": "Summarize Gmail inbox",
            "status": "defined",
            "humanControl": "Read-only until you connect Google.",
            "deliverables": "Inbox summary.",
        },
        {
            "id": "sk-gm-draft",
            "channelId": "gmail",
            "capabilityId": "cap-gm-compose",
            "name": "Draft Gmail reply",
            "status": "draft",
            "humanControl": "Approval required before send.",
            "deliverables": "Draft email body.",
        },
        {
            "id": "sk-cal-list",
            "channelId": "calendar",
            "capabilityId": "cap-cal-agenda",
            "name": "List upcoming events",
            "status": "defined",
            "humanControl": "Read-only calendar access.",
            "deliverables": "Agenda list.",
        },
        {
            "id": "sk-dr-search",
            "channelId": "drive",
            "capabilityId": "cap-dr-search",
            "name": "Search Drive files",
            "status": "defined",
            "humanControl": "Read-only Drive access.",
            "deliverables": "File matches.",
        },
    ],
    "ideas": [
        {
            "id": "idea-tg-triage",
            "title": "Telegram triage rules",
            "description": "Auto-label and prioritize chats once bot is stable.",
            "channelId": "telegram",
            "stage": "now",
            "owner": "You",
            "reach": 1,
            "impact": 2,
            "confidence": 80,
            "effort": 2,
            "createdAt": datetime.now(UTC).date().isoformat(),
        },
        {
            "id": "idea-gm-digest",
            "title": "Morning Gmail digest",
            "description": "Daily summary of unread important mail.",
            "channelId": "gmail",
            "stage": "next",
            "owner": "You",
            "reach": 1,
            "impact": 2,
            "confidence": 70,
            "effort": 3,
            "createdAt": datetime.now(UTC).date().isoformat(),
        },
        {
            "id": "idea-social-calendar",
            "title": "Cross-channel content calendar",
            "description": "One board for LinkedIn, X, Instagram once social connects.",
            "channelId": "linkedin",
            "stage": "later",
            "owner": "You",
            "reach": 1,
            "impact": 1,
            "confidence": 50,
            "effort": 5,
            "createdAt": datetime.now(UTC).date().isoformat(),
        },
    ],
    "boardNotes": [
        {
            "id": "note-welcome",
            "channelId": None,
            "text": "Personal Agent Hub — plan automations here. Live channels: Telegram + Google.",
            "x": 40,
            "y": 40,
        }
    ],
}


class HubStore:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def get_state(self) -> dict[str, Any]:
        with session_scope(self._sessions) as session:
            row = session.get(HubWorkspaceRow, "default")
            if row is None:
                row = HubWorkspaceRow(
                    id="default",
                    data_json=json.dumps(DEFAULT_HUB),
                    updated_at=datetime.now(UTC),
                )
                session.add(row)
                session.flush()
                return dict(DEFAULT_HUB)
            try:
                data = json.loads(row.data_json or "{}")
            except json.JSONDecodeError:
                data = {}
            return {
                "skills": data.get("skills") or DEFAULT_HUB["skills"],
                "ideas": data.get("ideas") or DEFAULT_HUB["ideas"],
                "boardNotes": data.get("boardNotes") or DEFAULT_HUB["boardNotes"],
            }

    def put_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = {
            "skills": list(payload.get("skills") or []),
            "ideas": list(payload.get("ideas") or []),
            "boardNotes": list(payload.get("boardNotes") or []),
        }
        with session_scope(self._sessions) as session:
            row = session.get(HubWorkspaceRow, "default")
            if row is None:
                row = HubWorkspaceRow(id="default")
                session.add(row)
            row.data_json = json.dumps(cleaned)
            row.updated_at = datetime.now(UTC)
            session.flush()
        return cleaned


class GoogleConnectionStore:
    def __init__(self, session_factory: sessionmaker, *, secret_key: str = "") -> None:
        self._sessions = session_factory
        self._secret_key = secret_key

    def status(self, *, oauth_configured: bool) -> dict[str, Any]:
        with session_scope(self._sessions) as session:
            row = session.get(GoogleConnectionRow, "default")
            connected_flag = bool(row and row.connected)
            has_tokens = bool(row and (row.refresh_token or row.access_token))
            email = (row.email if row else "") or ""
        # UI "connected" when OAuth is configured and a connection row is active.
        # Live list APIs still require sealed tokens (has_tokens).
        connected = connected_flag and oauth_configured
        return {
            "oauth_configured": oauth_configured,
            "connected": connected,
            "has_tokens": has_tokens and oauth_configured,
            "email": email if connected else "",
            "services": {
                "gmail": connected,
                "calendar": connected,
                "drive": connected,
            },
        }

    def save_tokens(
        self,
        *,
        email: str,
        access_token: str,
        refresh_token: str,
        scopes: str,
    ) -> None:
        from personal_agent.infrastructure.integrations.google.tokens import seal_token

        with session_scope(self._sessions) as session:
            row = session.get(GoogleConnectionRow, "default")
            if row is None:
                row = GoogleConnectionRow(id="default")
                session.add(row)
            row.connected = 1
            row.email = email
            row.access_token = seal_token(self._secret_key, access_token)
            if refresh_token:
                row.refresh_token = seal_token(self._secret_key, refresh_token)
            row.scopes = scopes
            row.updated_at = datetime.now(UTC)
            session.flush()

    def mark_connected(self, email: str = "local@dev") -> None:
        """Legacy helper for tests — marks connected without tokens (not live)."""
        with session_scope(self._sessions) as session:
            row = session.get(GoogleConnectionRow, "default")
            if row is None:
                row = GoogleConnectionRow(id="default")
                session.add(row)
            row.connected = 1
            row.email = email
            row.updated_at = datetime.now(UTC)
            session.flush()

    def load_tokens(self) -> dict[str, str]:
        from personal_agent.infrastructure.integrations.google.tokens import unseal_token

        with session_scope(self._sessions) as session:
            row = session.get(GoogleConnectionRow, "default")
            if row is None or not row.connected:
                return {"access_token": "", "refresh_token": "", "email": "", "scopes": ""}
            return {
                "access_token": unseal_token(self._secret_key, row.access_token or ""),
                "refresh_token": unseal_token(self._secret_key, row.refresh_token or ""),
                "email": row.email or "",
                "scopes": row.scopes or "",
            }

    def clear_tokens(self) -> dict[str, str]:
        """Clear connection and return plaintext tokens for revoke (best-effort)."""
        tokens = self.load_tokens()
        self.disconnect()
        return tokens

    def disconnect(self) -> None:
        with session_scope(self._sessions) as session:
            row = session.get(GoogleConnectionRow, "default")
            if row is None:
                return
            row.connected = 0
            row.email = ""
            row.access_token = ""
            row.refresh_token = ""
            row.scopes = ""
            row.updated_at = datetime.now(UTC)
            session.flush()
