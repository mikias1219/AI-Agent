"""Notes and diary: CRUD, search, diary-per-day rule and streak (contract section 1)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.life import (
    NOTE_BODY_MAX,
    LifeConflict,
    LifeError,
    Note,
    clean_note_create,
    clean_note_patch,
    page_args,
    parse_date,
    streak_days,
)
from personal_agent.domain.ports import NoteRepository

DIARY_DUPLICATE = "A diary entry for this date already exists."


class NoteService:
    def __init__(self, repository: NoteRepository, ctx: LifeContext) -> None:
        self._repo = repository
        self._ctx = ctx

    def create(self, owner: str, data: Mapping[str, Any], *, source: str = "owner") -> Note:
        fields = clean_note_create(data, today=self._ctx.today(owner))
        if fields["kind"] == "diary" and self._repo.find_diary(owner, fields["entry_date"]):
            raise LifeConflict(DIARY_DUPLICATE)
        now = self._ctx.now()
        note = Note(
            id=uuid.uuid4().hex,
            owner_user_id=owner,
            created_at=now,
            updated_at=now,
            **fields,
        )
        self._repo.add(note)
        self._ctx.record("note.created", owner, id=note.id, kind=note.kind, source=source)
        return note

    def get(self, owner: str, note_id: str) -> Note:
        note = self._repo.get(owner, note_id)
        if note is None:
            raise not_found("Note")
        return note

    def update(self, owner: str, note_id: str, data: Mapping[str, Any]) -> Note:
        note = self.get(owner, note_id)
        changes = clean_note_patch(note, data)
        new_date = changes.get("entry_date")
        if (
            isinstance(new_date, date)
            and new_date != note.entry_date
            and self._repo.find_diary(owner, new_date)
        ):
            raise LifeConflict(DIARY_DUPLICATE)
        if changes:
            for key, value in changes.items():
                setattr(note, key, value)
            note.updated_at = self._ctx.now()
            self._repo.save(note)
            self._ctx.record("note.updated", owner, id=note.id, fields=sorted(changes))
        return note

    def delete(self, owner: str, note_id: str) -> None:
        if not self._repo.delete(owner, note_id):
            raise not_found("Note")
        self._ctx.record("note.deleted", owner, id=note_id)

    def list(
        self,
        owner: str,
        *,
        kind: str | None = None,
        q: str = "",
        tag: str = "",
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Note]:
        if kind not in (None, "note", "diary"):
            raise LifeError("kind must be 'note' or 'diary'.")
        lim, off = page_args(limit, offset)
        return self._repo.list(
            owner, kind=kind, q=q.strip(), tag=tag.strip().lower(), limit=lim, offset=off
        )

    def search(self, owner: str, query: str, limit: int = 5) -> Sequence[Note]:
        return self._repo.list(
            owner, kind=None, q=query.strip(), tag="", limit=max(1, min(limit, 10)), offset=0
        )

    def stats(self, owner: str) -> dict[str, Any]:
        today = self._ctx.today(owner)
        dates: set[date] = set(self._repo.diary_dates(owner))
        return {
            "notes": self._repo.count(owner, "note"),
            "diary_entries": self._repo.count(owner, "diary"),
            "diary_streak_days": streak_days(dates, today),
            "wrote_diary_today": today in dates,
        }

    def recent_notes(self, owner: str, limit: int = 3) -> Sequence[Note]:
        return self._repo.recent(owner, "note", limit)

    def diary_append(
        self,
        owner: str,
        body: str,
        *,
        mood: str | None = None,
        entry_date: str | None = None,
        source: str = "agent",
    ) -> tuple[Note, bool]:
        """Append to the day's entry when one exists. Returns (note, appended)."""
        day = parse_date(entry_date, "entry_date") if entry_date else self._ctx.today(owner)
        existing = self._repo.find_diary(owner, day)
        if existing is None:
            data: dict[str, Any] = {
                "kind": "diary",
                "body": body,
                "entry_date": day.isoformat(),
                "mood": mood,
            }
            return self.create(owner, data, source=source), False
        text = body.strip()
        if not text:
            raise LifeError("Diary text is empty.")
        merged = f"{existing.body.rstrip()}\n\n{text}" if existing.body.strip() else text
        if len(merged) > NOTE_BODY_MAX:
            raise LifeError(f"The diary entry would exceed {NOTE_BODY_MAX} characters.")
        patch: dict[str, Any] = {"body": merged}
        if mood is not None:
            patch["mood"] = mood
        return self.update(owner, existing.id, patch), True
