"""JSON shapes for the life modules (docs/LIFE_API_CONTRACT.md). Used by routes, tools, export."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from personal_agent.domain.drive_sync import DriveLink
from personal_agent.domain.life import FileItem, LearnItem, Note, ReadingLog, ReadingPlan


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def drive_fields(link: DriveLink | None) -> dict[str, Any]:
    """`drive_url` and `drive_synced_at` (null until the object is backed up to Drive)."""
    if link is None or link.local_deleted_at is not None:
        return {"drive_url": None, "drive_synced_at": None}
    return {"drive_url": link.drive_url or None, "drive_synced_at": _iso(link.synced_at)}


def note_payload(note: Note, link: DriveLink | None = None) -> dict[str, Any]:
    return {
        "id": note.id,
        "kind": note.kind,
        "title": note.title,
        "body": note.body,
        "tags": list(note.tags),
        "mood": note.mood,
        "entry_date": _iso(note.entry_date),
        "pinned": note.pinned,
        "created_at": _iso(note.created_at),
        "updated_at": _iso(note.updated_at),
        **drive_fields(link),
    }


def file_payload(item: FileItem, link: DriveLink | None = None) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "mime": item.mime,
        "size": item.size,
        "kind": item.kind,
        "description": item.description,
        "tags": list(item.tags),
        "created_at": _iso(item.created_at),
        "url": f"/api/files/{item.id}/content",
        **drive_fields(link),
    }


def learn_payload(item: LearnItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "term": item.term,
        "meaning": item.meaning,
        "example": item.example,
        "language": item.language,
        "topic": item.topic,
        "box": item.box,
        "next_review_at": _iso(item.next_review_at),
        "times_correct": item.times_correct,
        "times_wrong": item.times_wrong,
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }


def plan_payload(plan: ReadingPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "name": plan.name,
        "items": list(plan.items),
        "position": plan.position,
        "active": plan.active,
        "created_at": _iso(plan.created_at),
        "updated_at": _iso(plan.updated_at),
        "next": plan.next,
        "progress": plan.progress,
    }


def reading_log_payload(log: ReadingLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "reference": log.reference,
        "read_on": _iso(log.read_on),
        "reflection": log.reflection,
        "plan_id": log.plan_id,
        "created_at": _iso(log.created_at),
    }
