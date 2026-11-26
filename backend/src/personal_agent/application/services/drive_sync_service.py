"""Google Drive backup of Compass data (contract section 8, ADR 0035).

Compass is the source of truth. This service never reads Drive content and never deletes
anything in Drive: a local delete only marks the link. A run is two steps:

1. `request_push` builds a *snapshot* (at most 50 objects whose content hash changed) and asks
   the tool registry to run `drive_sync_push` with exactly that snapshot. With mode `ask` the
   registry records one approval that lists counts and titles; with mode `auto` it runs.
2. `execute_push` (the tool handler) writes exactly those objects, creating folders under one
   `Compass` folder once and overwriting existing Drive files in place.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol

from personal_agent.application.services.day_service import DayService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.sync_common import (
    READ_ONLY_MESSAGE,
    SyncUnavailable,
    mode_label,
    run_batch,
    scope_granted,
)
from personal_agent.domain.days import summarize
from personal_agent.domain.drive_sync import (
    DRIVE_FILE_SCOPE,
    INCLUDE_KEYS,
    MAX_BATCH,
    ROOT_FOLDER,
    DriveLink,
    DriveObject,
    SyncSettings,
    daily_object,
    diary_object,
    file_meta_hash,
    file_object,
    note_object,
    reading_object,
    vocabulary_object,
)
from personal_agent.domain.exceptions import IntegrationError
from personal_agent.domain.life import LifeError
from personal_agent.domain.ports import (
    AuditLog,
    DriveLinkStore,
    FileRepository,
    LearnRepository,
    NoteRepository,
    ReadingRepository,
    SyncSettingsStore,
    ToolRegistry,
)

logger = logging.getLogger(__name__)

NOT_CONNECTED = "Google Drive is not connected."
RECONNECT = "Reconnect Google to allow Drive backup."
SERVICE = "drive"
TOOL = "drive_sync_push"
_ALL = 100_000
_ABORT_STATUSES = (401, 403)


class DriveClient(Protocol):
    def drive_find_or_create_folder(
        self, *, name: str, parent_id: str | None = None
    ) -> dict[str, Any]: ...

    def drive_upsert_file(
        self,
        *,
        name: str,
        content: bytes,
        mime: str,
        parent_id: str,
        file_id: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(slots=True)
class _Candidate:
    object_type: str
    object_id: str
    title: str
    hash: str
    build: Callable[[], DriveObject]
    group: str  # include key and pending-count key


class DriveSyncService:
    def __init__(
        self,
        *,
        links: DriveLinkStore,
        settings: SyncSettingsStore,
        notes: NoteRepository,
        files: FileRepository,
        learn: LearnRepository,
        reading: ReadingRepository,
        days: DayService,
        profiles: ProfileService,
        client: DriveClient,
        registry: ToolRegistry,
        google_status: Callable[[], Mapping[str, Any]],
        approval_required: Callable[[], bool],
        audit: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._links = links
        self._settings = settings
        self._notes = notes
        self._files = files
        self._learn = learn
        self._reading = reading
        self._days = days
        self._profiles = profiles
        self._client = client
        self._registry = registry
        self._google_status = google_status
        self._approval_required = approval_required
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))

    # -- connection state ----------------------------------------------------------------

    def connection(self) -> tuple[bool, bool, bool]:
        """(connected, scope_granted, read_only)."""
        status = self._google_status()
        connected = bool(status.get("connected"))
        return (
            connected,
            scope_granted(status, DRIVE_FILE_SCOPE),
            bool(status.get("read_only", True)),
        )

    def require_ready(self) -> None:
        connected, granted, read_only = self.connection()
        if not connected:
            raise SyncUnavailable(NOT_CONNECTED)
        if not granted:
            raise SyncUnavailable(RECONNECT)
        if read_only:
            raise SyncUnavailable(READ_ONLY_MESSAGE)

    # -- settings and status --------------------------------------------------------------

    def get_settings(self, owner: str) -> SyncSettings:
        return self._settings.get(owner, SERVICE)

    def update_settings(
        self, owner: str, *, enabled: bool | None = None, include: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        current = self._settings.get(owner, SERVICE)
        if enabled is not None:
            if not isinstance(enabled, bool):
                raise LifeError("enabled must be true or false.")
            current.enabled = enabled
        if include is not None:
            if not isinstance(include, Mapping):
                raise LifeError("include must be an object.")
            merged = {key: current.includes(key) for key in INCLUDE_KEYS}
            for key, value in include.items():
                if key not in INCLUDE_KEYS:
                    raise LifeError(f"include.{key} is not a Drive sync group.")
                if not isinstance(value, bool):
                    raise LifeError(f"include.{key} must be true or false.")
                merged[key] = value
            current.include = merged
        self._settings.save(current)
        if self._audit is not None:
            self._audit.record(
                "drive_sync.settings_updated",
                owner,
                {"enabled": current.enabled, "include": dict(current.include)},
            )
        return self.status(owner)

    def mode(self) -> str:
        return mode_label(self._approval_required())

    def status(self, owner: str) -> dict[str, Any]:
        self.reconcile(owner)
        connected, granted, _ro = self.connection()
        settings = self._settings.get(owner, SERVICE)
        counts = self.pending_counts(owner)
        root = self._links.get_folder(owner, ROOT_FOLDER)
        return {
            "connected": connected,
            "scope_granted": granted,
            "enabled": settings.enabled,
            "mode": self.mode(),
            "root_url": root[1] if root and root[1] else None,
            "last_sync_at": settings.last_sync_at.isoformat() if settings.last_sync_at else None,
            "last_error": settings.last_error or None,
            "include": {key: settings.includes(key) for key in INCLUDE_KEYS},
            "pending": counts,
        }

    def items(
        self, owner: str, *, object_type: str | None, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        self.reconcile(owner)
        if not 1 <= limit <= 200 or offset < 0:
            raise LifeError("limit must be between 1 and 200 and offset 0 or more.")
        rows = self._links.list(owner, object_type=object_type or None, limit=limit, offset=offset)
        return [
            {
                "object_type": link.object_type,
                "object_id": link.object_id,
                "drive_file_id": link.drive_file_id,
                "drive_url": link.drive_url or None,
                "synced_at": link.synced_at.isoformat(),
            }
            for link in rows
        ]

    def link_map(
        self, owner: str, object_types: Sequence[str], object_ids: Sequence[str]
    ) -> dict[str, DriveLink]:
        """Live links (not marked deleted) by object id, for the Notes and Files payloads."""
        found = self._links.for_objects(owner, object_types, object_ids)
        return {link.object_id: link for link in found if link.local_deleted_at is None}

    # -- candidates -----------------------------------------------------------------------

    def _candidates(self, owner: str) -> list[_Candidate]:
        settings = self._settings.get(owner, SERVICE)
        tz = self._profiles.timezone_for(owner)
        today = self._days.today(owner)
        out: list[_Candidate] = []

        if settings.includes("daily"):
            out += self._daily_candidates(owner, today)
        if settings.includes("diary"):
            for note in self._notes.list(owner, kind="diary", q="", tag="", limit=_ALL, offset=0):
                obj = diary_object(note, tz)
                out.append(
                    _Candidate("diary", note.id, obj.title, obj.content_hash, _fixed(obj), "diary")
                )
        if settings.includes("notes"):
            for note in self._notes.list(owner, kind="note", q="", tag="", limit=_ALL, offset=0):
                obj = note_object(note, tz)
                out.append(
                    _Candidate("note", note.id, obj.title, obj.content_hash, _fixed(obj), "notes")
                )
        if settings.includes("files"):
            for item in self._files.list(owner, kind=None, q="", tag="", limit=_ALL, offset=0):
                out.append(
                    _Candidate(
                        "file",
                        item.id,
                        item.name,
                        file_meta_hash(item, tz),
                        self._file_loader(owner, item.id, tz),
                        "files",
                    )
                )
        if settings.includes("learning"):
            words = self._learn.list(
                owner, q="", topic="", language="", due_at=None, limit=_ALL, offset=0
            )
            if words:
                obj = vocabulary_object(words)
                out.append(
                    _Candidate(
                        "learning",
                        obj.object_id,
                        obj.title,
                        obj.content_hash,
                        _fixed(obj),
                        "learning",
                    )
                )
        if settings.includes("reading"):
            logs = self._reading.list_logs(owner, plan_id="", limit=_ALL, offset=0)
            if logs:
                obj = reading_object(logs)
                out.append(
                    _Candidate(
                        "reading",
                        obj.object_id,
                        obj.title,
                        obj.content_hash,
                        _fixed(obj),
                        "reading",
                    )
                )
        return out

    def _daily_candidates(self, owner: str, today: date) -> list[_Candidate]:
        grouped: dict[date, list[Any]] = defaultdict(list)
        for task in self._days.tasks_until(owner, today):
            if task.plan_date is not None:
                grouped[task.plan_date].append(task)
        if not grouped:
            return []
        readings: dict[date, list[Any]] = defaultdict(list)
        for log in self._reading.list_logs(owner, plan_id="", limit=_ALL, offset=0):
            readings[log.read_on].append(log)
        out: list[_Candidate] = []
        for day in sorted(grouped, reverse=True):
            tasks = grouped[day]
            obj = daily_object(
                day,
                tasks,
                summarize(tasks),
                readings=readings.get(day, []),
                reviewed=self._days.reviewed_on(owner, day),
            )
            out.append(
                _Candidate(
                    "daily", obj.object_id, obj.title, obj.content_hash, _fixed(obj), "daily"
                )
            )
        return out

    def _file_loader(self, owner: str, file_id: str, tz: str) -> Callable[[], DriveObject]:
        def load() -> DriveObject:
            found = self._files.get_content(owner, file_id)
            if found is None:
                raise LifeError("File no longer exists.")
            return file_object(found[0], found[1], tz)

        return load

    def _stored_hash(self, owner: str, cand: _Candidate) -> str | None:
        link = self._links.get(owner, cand.object_type, cand.object_id)
        if link is None or link.local_deleted_at is not None:
            return None
        return link.content_hash

    def pending(self, owner: str) -> list[_Candidate]:
        return [c for c in self._candidates(owner) if self._stored_hash(owner, c) != c.hash]

    def pending_counts(self, owner: str) -> dict[str, Any]:
        found = self.pending(owner)

        def count(group: str) -> int:
            return sum(1 for c in found if c.group == group)

        return {
            "notes": count("notes"),
            "diary": count("diary"),
            "daily": count("daily"),
            "files": count("files"),
            "learning": count("learning") > 0,
            "reading": count("reading") > 0,
        }

    def snapshot(self, owner: str) -> tuple[list[dict[str, str]], int]:
        """(first 50 pending objects as `{type, id, title}`, how many more are pending)."""
        found = self.pending(owner)
        chosen = found[:MAX_BATCH]
        items = [{"type": c.object_type, "id": c.object_id, "title": c.title[:120]} for c in chosen]
        return items, max(0, len(found) - len(chosen))

    # -- requesting a push ------------------------------------------------------------------

    def request_push(self, owner: str, *, origin: str = "dashboard") -> dict[str, Any]:
        """Run the Drive batch through the registry: one approval (ask) or straight through."""
        self.require_ready()
        items, _more = self.snapshot(owner)
        if not items:
            return {"status": "nothing_to_do", "approval_id": None, "summary": None}
        return run_batch(
            self._registry,
            owner=owner,
            origin=origin,
            session="drive-sync",
            tool=TOOL,
            arguments={"items": items},
        )

    # -- executing the approved snapshot (the tool handler) ---------------------------------------

    def execute_push(self, owner: str, items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        self.require_ready()
        if len(items) > MAX_BATCH:
            raise LifeError(f"A Drive batch holds at most {MAX_BATCH} objects.")
        by_key = {(c.object_type, c.object_id): c for c in self._candidates(owner)}
        tz_now = self._clock()
        counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
        errors: list[str] = []
        for item in items:
            key = (str(item.get("type")), str(item.get("id")))
            candidate = by_key.get(key)
            if candidate is None:
                counts["failed"] += 1
                errors.append(f"{key[0]} {key[1]}: not found or not included")
                continue
            if self._stored_hash(owner, candidate) == candidate.hash:
                counts["skipped"] += 1
                continue
            try:
                kind = self._write(owner, candidate, tz_now)
            except IntegrationError as exc:
                if exc.status_code in _ABORT_STATUSES:
                    self._remember(owner, tz_now, str(exc))
                    raise
                counts["failed"] += 1
                errors.append(f"{candidate.title[:60]}: {exc}")
                continue
            except LifeError as exc:
                counts["failed"] += 1
                errors.append(f"{candidate.title[:60]}: {exc}")
                continue
            counts[kind] += 1
        self._remember(owner, tz_now, errors[0] if errors else "", ok=counts["failed"] == 0)
        if self._audit is not None:
            self._audit.record(
                "drive_sync.pushed",
                owner,
                {**counts, "objects": [f"{i.get('type')}:{i.get('id')}" for i in items]},
            )
        summary = (
            f"Drive backup: {counts['created']} created, {counts['updated']} updated, "
            f"{counts['skipped']} unchanged, {counts['failed']} failed."
        )
        return {
            "result_type": "drive_sync",
            "summary": summary,
            **counts,
            "errors": errors[:10],
        }

    def _remember(self, owner: str, when: datetime, error: str, *, ok: bool = True) -> None:
        settings = self._settings.get(owner, SERVICE)
        if ok:
            settings.last_sync_at = when
        settings.last_error = error[:500]
        self._settings.save(settings)

    def _write(self, owner: str, cand: _Candidate, now: datetime) -> str:
        obj = cand.build()
        parent_id = self._folder_chain(owner, obj.folders)
        link = self._links.get(owner, cand.object_type, cand.object_id)
        file_id = link.drive_file_id if link and link.local_deleted_at is None else None
        kind = "updated" if file_id else "created"
        try:
            result = self._upsert(owner, obj, parent_id, file_id)
        except IntegrationError as exc:
            if exc.status_code != 404:
                raise
            # The Drive file or folder was removed by the owner: rebuild the folders and
            # create a fresh copy. Nothing is ever deleted by Compass.
            self._links.drop_folders(owner)
            parent_id = self._folder_chain(owner, obj.folders)
            result = self._upsert(owner, obj, parent_id, None)
            kind = "created"
        self._links.put(
            DriveLink(
                id=link.id if link else uuid.uuid4().hex,
                owner_user_id=owner,
                object_type=cand.object_type,
                object_id=cand.object_id,
                drive_file_id=str(result["id"]),
                drive_url=str(result.get("url") or ""),
                content_hash=cand.hash,
                synced_at=now,
                local_deleted_at=None,
            )
        )
        return kind

    def _upsert(
        self, owner: str, obj: DriveObject, parent_id: str, file_id: str | None
    ) -> dict[str, Any]:
        del owner
        return self._client.drive_upsert_file(
            name=obj.filename,
            content=obj.content,
            mime=obj.mime,
            parent_id=parent_id,
            file_id=file_id,
        )

    def _folder_chain(self, owner: str, folders: Sequence[str]) -> str:
        """Find or create Compass/<folders...>; every folder id is cached after its first lookup."""
        parts = [ROOT_FOLDER, *folders]
        parent: str | None = None
        path = ""
        for name in parts:
            path = f"{path}/{name}" if path else name
            cached = self._links.get_folder(owner, path)
            if cached is not None:
                parent = cached[0]
                continue
            found = self._client.drive_find_or_create_folder(name=name, parent_id=parent)
            self._links.put_folder(owner, path, str(found["id"]), str(found.get("url") or ""))
            parent = str(found["id"])
        assert parent is not None
        return parent

    # -- local deletes ----------------------------------------------------------------------

    def reconcile(self, owner: str) -> None:
        """Mark links whose Compass object is gone. The Drive copy is left exactly as it is."""
        for link in self._links.list(owner, object_type=None, limit=_ALL, offset=0):
            if link.local_deleted_at is not None:
                continue
            gone = False
            if link.object_type in ("note", "diary"):
                gone = self._notes.get(owner, link.object_id) is None
            elif link.object_type == "file":
                gone = self._files.get(owner, link.object_id) is None
            if gone:
                self._links.mark_local_deleted(owner, link.object_type, link.object_id)

    # -- export and wipe (BR-13) -----------------------------------------------------------

    def export(self, owner: str) -> dict[str, Any]:
        return {
            "drive_links": [
                {
                    "object_type": link.object_type,
                    "object_id": link.object_id,
                    "drive_file_id": link.drive_file_id,
                    "drive_url": link.drive_url,
                    "content_hash": link.content_hash,
                    "synced_at": link.synced_at.isoformat(),
                    "local_deleted_at": (
                        link.local_deleted_at.isoformat() if link.local_deleted_at else None
                    ),
                }
                for link in self._links.list(owner, object_type=None, limit=_ALL, offset=0)
            ],
            "sync_settings": [
                _settings_dict(self._settings.get(owner, service))
                for service in ("drive", "calendar")
            ],
        }

    def wipe(self, owner: str) -> dict[str, int]:
        """Forget links, folder ids and sync settings. Nothing in Drive is touched."""
        return {
            "drive_links": self._links.delete_all(owner),
            "sync_settings": self._settings.delete_all(owner),
        }


def _fixed(obj: DriveObject) -> Callable[[], DriveObject]:
    return lambda: obj


def _settings_dict(settings: SyncSettings) -> dict[str, Any]:
    return {
        "service": settings.service,
        "enabled": settings.enabled,
        "include": dict(settings.include),
        "last_sync_at": settings.last_sync_at.isoformat() if settings.last_sync_at else None,
        "last_error": settings.last_error,
    }
