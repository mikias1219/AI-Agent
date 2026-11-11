"""Google OAuth connection persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import sessionmaker

from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import GoogleConnectionRow


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
