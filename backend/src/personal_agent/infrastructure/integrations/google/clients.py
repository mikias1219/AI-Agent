"""Read-only Google product list clients shaped for the Next.js UI."""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

import httpx

GMAIL_LIST = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_GET = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{id}"
GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
CALENDAR_LIST = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
DRIVE_LIST = "https://www.googleapis.com/drive/v3/files"


class GoogleApiError(RuntimeError):
    pass


class GoogleApiClient:
    def __init__(
        self,
        *,
        access_token_provider: Callable[[], str],
        http_client: httpx.Client | None = None,
    ) -> None:
        self._access_token_provider = access_token_provider
        self._http = http_client

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token_provider()}"}

    def _get(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = self._client()
        owns = self._http is None
        try:
            response = client.get(url, headers=self._headers(), params=params or {})
            if response.status_code >= 400:
                raise GoogleApiError(f"Google API error ({response.status_code}) for {url}.")
            return response.json()
        finally:
            if owns:
                client.close()

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        owns = self._http is None
        try:
            response = client.post(url, headers=self._headers(), json=body)
            if response.status_code >= 400:
                raise GoogleApiError(f"Google API error ({response.status_code}) for {url}.")
            return response.json()
        finally:
            if owns:
                client.close()

    def _patch(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        owns = self._http is None
        try:
            response = client.patch(url, headers=self._headers(), json=body)
            if response.status_code >= 400:
                raise GoogleApiError(f"Google API error ({response.status_code}) for {url}.")
            return response.json()
        finally:
            if owns:
                client.close()

    def send_gmail(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        message = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        raw = base64.urlsafe_b64encode(message.encode()).decode().rstrip("=")
        return self._post(GMAIL_SEND, {"raw": raw})

    def create_calendar_event(
        self,
        *,
        title: str,
        starts_at: str,
        ends_at: str,
        location: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": starts_at, "timeZone": "UTC"},
            "end": {"dateTime": ends_at, "timeZone": "UTC"},
        }
        if location:
            payload["location"] = location
        return self._post(CALENDAR_LIST, payload)

    def update_calendar_event(
        self,
        *,
        event_id: str,
        title: str | None = None,
        starts_at: str | None = None,
        ends_at: str | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if title is not None:
            payload["summary"] = title
        if starts_at is not None:
            payload["start"] = {"dateTime": starts_at, "timeZone": "UTC"}
        if ends_at is not None:
            payload["end"] = {"dateTime": ends_at, "timeZone": "UTC"}
        if location is not None:
            payload["location"] = location
        url = f"{CALENDAR_LIST}/{event_id}"
        return self._patch(url, payload)

    def list_gmail(self, *, page: int, page_size: int) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(max(1, page_size), 50)
        # Gmail uses page tokens; for UI parity fetch a bounded recent window then slice.
        listing = self._get(
            GMAIL_LIST,
            params={"maxResults": min(page * page_size, 50), "q": "in:inbox"},
        )
        refs = listing.get("messages") or []
        total = len(refs)
        start = (page - 1) * page_size
        chunk = refs[start : start + page_size]
        items: list[dict[str, Any]] = []
        for ref in chunk:
            detail = self._get(
                GMAIL_GET.format(id=ref["id"]),
                params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
            )
            headers = {
                h["name"].lower(): h.get("value", "")
                for h in (detail.get("payload") or {}).get("headers") or []
            }
            items.append(
                {
                    "id": detail.get("id") or ref["id"],
                    "from": headers.get("from", ""),
                    "subject": headers.get("subject", "(no subject)"),
                    "snippet": detail.get("snippet") or "",
                    "receivedAt": _epoch_ms_to_iso(detail.get("internalDate")),
                }
            )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    def list_calendar(self, *, page: int, page_size: int) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(max(1, page_size), 50)
        listing = self._get(
            CALENDAR_LIST,
            params={
                "maxResults": min(page * page_size, 50),
                "singleEvents": "true",
                "orderBy": "startTime",
                "timeMin": "1970-01-01T00:00:00Z",
            },
        )
        events = listing.get("items") or []
        total = len(events)
        start = (page - 1) * page_size
        chunk = events[start : start + page_size]
        items = []
        for event in chunk:
            start_info = event.get("start") or {}
            starts = start_info.get("dateTime") or start_info.get("date") or ""
            items.append(
                {
                    "id": event.get("id") or "",
                    "title": event.get("summary") or "(no title)",
                    "startsAt": starts,
                    "location": event.get("location") or "",
                }
            )
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    def list_drive(self, *, page: int, page_size: int) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(max(1, page_size), 50)
        listing = self._get(
            DRIVE_LIST,
            params={
                "pageSize": min(page * page_size, 50),
                "fields": "files(id,name,mimeType,modifiedTime)",
                "q": "trashed=false",
                "orderBy": "modifiedTime desc",
            },
        )
        files = listing.get("files") or []
        total = len(files)
        start = (page - 1) * page_size
        chunk = files[start : start + page_size]
        items = [
            {
                "id": f.get("id") or "",
                "name": f.get("name") or "(unnamed)",
                "kind": f.get("mimeType") or "file",
                "updatedAt": f.get("modifiedTime") or "",
            }
            for f in chunk
        ]
        return {"items": items, "page": page, "page_size": page_size, "total": total}


def _epoch_ms_to_iso(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return str(value)
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat().replace("+00:00", "Z")
