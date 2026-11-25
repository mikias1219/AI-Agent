"""Export and wipe for the life modules (BR-13): notes, diary, files, learning, reading, photo."""

from __future__ import annotations

import base64
from typing import Any

from personal_agent.application.life_payloads import (
    file_payload,
    learn_payload,
    note_payload,
    plan_payload,
    reading_log_payload,
)
from personal_agent.domain.ports import (
    FileRepository,
    LearnRepository,
    NoteRepository,
    ProfilePhotoRepository,
    ReadingRepository,
)

_ALL = 100_000


class LifeDataService:
    def __init__(
        self,
        *,
        notes: NoteRepository,
        files: FileRepository,
        learn: LearnRepository,
        reading: ReadingRepository,
        photos: ProfilePhotoRepository,
    ) -> None:
        self._notes = notes
        self._files = files
        self._learn = learn
        self._reading = reading
        self._photos = photos

    def export(self, owner: str) -> dict[str, Any]:
        from datetime import UTC, datetime

        file_rows = []
        for item in self._files.list(owner, kind=None, q="", tag="", limit=_ALL, offset=0):
            found = self._files.get_content(owner, item.id)
            payload = file_payload(item)
            payload["data_base64"] = base64.b64encode(found[1]).decode("ascii") if found else ""
            file_rows.append(payload)
        photo = self._photos.get(owner)
        return {
            "notes": [
                note_payload(n)
                for n in self._notes.list(owner, kind=None, q="", tag="", limit=_ALL, offset=0)
            ],
            "files": file_rows,
            "learn_items": [
                learn_payload(i)
                for i in self._learn.list(
                    owner,
                    q="",
                    topic="",
                    language="",
                    due_at=None,
                    limit=_ALL,
                    offset=0,
                )
            ],
            "learn_reviews": self._learn.all_reviews(owner),
            "reading_plans": [
                plan_payload(p) for p in self._reading.list_plans(owner, limit=_ALL, offset=0)
            ],
            "reading_logs": [
                reading_log_payload(log)
                for log in self._reading.list_logs(owner, plan_id="", limit=_ALL, offset=0)
            ],
            "profile_photo": (
                {
                    "mime": photo.mime,
                    "data_base64": base64.b64encode(photo.content).decode("ascii"),
                    "updated_at": photo.updated_at.astimezone(UTC).isoformat()
                    if isinstance(photo.updated_at, datetime)
                    else None,
                }
                if photo
                else None
            ),
        }

    def wipe(self, owner: str) -> dict[str, int]:
        return {
            "notes": self._notes.delete_all(owner),
            "files": self._files.delete_all(owner),
            "learn_items": self._learn.delete_all(owner),
            "reading_plans": self._reading.delete_all(owner),
            "profile_photo": 1 if self._photos.delete(owner) else 0,
        }
