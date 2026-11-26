"""Drive layout, Markdown renderers and sync records — pure functions (contract section 8).

Layout under one `Compass` folder (filenames are slugged; never `/`, `..` or control characters):

    Notes/{YYYY}/{YYYY-MM}/{title-slug}-{id8}.md
    Diary/{YYYY}/{YYYY-MM}/{YYYY-MM-DD}.md
    Daily/{YYYY}/{YYYY-MM}/{YYYY-MM-DD}-summary.md
    Learning/vocabulary.md
    Reading/reading-log.md
    Files/{YYYY}/{YYYY-MM}/{original file name}

Every Markdown file starts with YAML front matter (`id`, `kind`, `tags`, `created`,
`updated`). Values are written as JSON, which is valid YAML, so titles and tags can never
break out of the front matter.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from personal_agent.domain.days import DaySummary, day_line, effective_outcome
from personal_agent.domain.life import FileItem, LearnItem, Note, ReadingLog
from personal_agent.domain.models import Task

ROOT_FOLDER = "Compass"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
MAX_BATCH = 50
MAX_NAME_LENGTH = 120
MAX_VOCABULARY_ROWS = 5000
MAX_READING_ROWS = 5000

OBJECT_TYPES = ("note", "diary", "daily", "file", "learning", "reading")
INCLUDE_KEYS = ("notes", "diary", "daily", "files", "learning", "reading")
VOCABULARY_ID = "vocabulary"
READING_ID = "reading-log"

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(slots=True)
class DriveLink:
    id: str
    owner_user_id: str
    object_type: str
    object_id: str
    drive_file_id: str
    drive_url: str
    content_hash: str
    synced_at: datetime
    local_deleted_at: datetime | None = None


@dataclass(slots=True)
class SyncSettings:
    owner_user_id: str
    service: str  # "drive" | "calendar"
    enabled: bool = False
    include: dict[str, bool] = field(default_factory=dict)
    last_sync_at: datetime | None = None
    last_error: str = ""

    def includes(self, key: str) -> bool:
        return bool(self.include.get(key, True))


@dataclass(frozen=True, slots=True)
class DriveObject:
    """One thing ready to be written: where it goes and exactly what the bytes are."""

    object_type: str
    object_id: str
    title: str
    folders: tuple[str, ...]
    filename: str
    content: bytes
    mime: str

    @property
    def content_hash(self) -> str:
        return content_hash(self.folders, self.filename, self.content)


def content_hash(folders: Sequence[str], filename: str, content: bytes) -> str:
    digest = hashlib.sha256()
    digest.update("/".join(folders).encode("utf-8"))
    digest.update(b"\0")
    digest.update(filename.encode("utf-8"))
    digest.update(b"\0")
    digest.update(content)
    return digest.hexdigest()


# -- names -------------------------------------------------------------------------------


def slugify(text: str, *, fallback: str = "untitled", max_length: int = MAX_NAME_LENGTH) -> str:
    """Lowercase letters and digits (any script) joined by single dashes; never `.`, `/`, `\\`."""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    out: list[str] = []
    for char in normalized:
        out.append(char if char.isalnum() else "-")
    slug = re.sub(r"-+", "-", "".join(out)).strip("-")
    slug = slug[:max_length].strip("-")
    return slug or fallback


def safe_filename(name: str, *, fallback: str = "file", max_length: int = 200) -> str:
    """Keep the original file name but drop folders, control characters and `..`."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = _CONTROL.sub("", base)
    base = base.replace("‮", "")  # right-to-left override tricks
    while ".." in base:
        base = base.replace("..", ".")
    base = base.strip(" .")
    if len(base) > max_length:
        stem, dot, ext = base.rpartition(".")
        if dot and len(ext) <= 10:
            base = stem[: max_length - len(ext) - 1] + "." + ext
        else:
            base = base[:max_length]
    return base or fallback


def is_safe_drive_name(name: str) -> bool:
    return bool(
        name
        and len(name) <= 255
        and "/" not in name
        and "\\" not in name
        and ".." not in name
        and not _CONTROL.search(name)
    )


def _zone(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except Exception:  # noqa: BLE001 - unknown zone: fall back to UTC
        return ZoneInfo("UTC")


def _local(moment: datetime, timezone: str) -> datetime:
    aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
    return aware.astimezone(_zone(timezone))


def _year_month(day: date) -> tuple[str, str]:
    return f"{day.year:04d}", f"{day.year:04d}-{day.month:02d}"


# -- front matter and small helpers ------------------------------------------------------


def front_matter(*, id: str, kind: str, tags: Iterable[str], created: str, updated: str) -> str:
    """YAML front matter with JSON-encoded values (valid YAML, injection-proof)."""
    tag_list = json.dumps([str(t) for t in tags], ensure_ascii=False)
    return (
        "---\n"
        f"id: {json.dumps(id, ensure_ascii=False)}\n"
        f"kind: {json.dumps(kind)}\n"
        f"tags: {tag_list}\n"
        f"created: {json.dumps(created)}\n"
        f"updated: {json.dumps(updated)}\n"
        "---\n"
    )


def _iso(moment: datetime) -> str:
    aware = moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat()


def _cell(value: object) -> str:
    text = str(value if value is not None else "")
    text = _CONTROL.sub(" ", text).replace("|", "\\|")
    return re.sub(r"\s+", " ", text).strip()


def _number(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


# -- renderers ---------------------------------------------------------------------------


def render_note(note: Note) -> str:
    heading = note.title.strip() or "Untitled"
    head = front_matter(
        id=note.id,
        kind="note",
        tags=note.tags,
        created=_iso(note.created_at),
        updated=_iso(note.updated_at),
    )
    return f"{head}\n# {_single_line(heading)}\n\n{note.body.strip()}\n"


def render_diary(note: Note) -> str:
    day = note.entry_date.isoformat() if note.entry_date else note.created_at.date().isoformat()
    head = front_matter(
        id=note.id,
        kind="diary",
        tags=note.tags,
        created=_iso(note.created_at),
        updated=_iso(note.updated_at),
    )
    mood = f"Mood: {note.mood}\n\n" if note.mood else ""
    return f"{head}\n# Diary {day}\n\n{mood}{note.body.strip()}\n"


def render_daily(
    day: date,
    tasks: Sequence[Task],
    summary: DaySummary,
    *,
    readings: Sequence[ReadingLog] = (),
    reviewed: int = 0,
) -> str:
    updated = max((t.updated_at for t in tasks if t.updated_at), default=None)
    head = front_matter(
        id=f"daily-{day.isoformat()}",
        kind="daily",
        tags=["daily"],
        created=day.isoformat(),
        updated=_iso(updated) if updated else day.isoformat(),
    )
    lines = [head, f"# {day.isoformat()}", "", f"**{day_line(summary)}**", ""]
    lines += [
        f"- planned: {summary.planned}",
        f"- achieved: {summary.achieved}",
        f"- partial: {summary.partial}",
        f"- missed: {summary.missed}",
        f"- skipped: {summary.skipped}",
        f"- open: {summary.open}",
        "",
        "## Tasks",
        "",
    ]
    if tasks:
        lines += ["| Task | Outcome | Target | Done | Note |", "| --- | --- | --- | --- | --- |"]
        for task in tasks:
            outcome = effective_outcome(task) or task.status.value
            target = f"{_number(task.target_value)} {task.target_unit}".strip()
            done = f"{_number(task.actual_value)} {task.target_unit}".strip()
            lines.append(
                f"| {_cell(task.title)} | {_cell(outcome)} | {_cell(target)} | "
                f"{_cell(done if task.actual_value is not None else '')} | "
                f"{_cell(task.outcome_note)} |"
            )
    else:
        lines.append("No tasks.")
    lines += ["", "## Reading", ""]
    if readings:
        lines += [
            f"- {_cell(r.reference)}" + (f": {_cell(r.reflection)}" if r.reflection else "")
            for r in readings
        ]
    else:
        lines.append("Nothing logged.")
    lines += ["", "## Learning", "", f"Words reviewed: {reviewed}", ""]
    return "\n".join(lines)


def render_vocabulary(items: Sequence[LearnItem]) -> str:
    rows = sorted(items, key=lambda i: (i.language, i.term.casefold()))[:MAX_VOCABULARY_ROWS]
    updated = max((i.updated_at for i in items), default=None)
    created = min((i.created_at for i in items), default=None)
    head = front_matter(
        id=VOCABULARY_ID,
        kind="learning",
        tags=["vocabulary"],
        created=_iso(created) if created else "",
        updated=_iso(updated) if updated else "",
    )
    lines = [head, "# Vocabulary", "", "| Term | Meaning | Example | Language | Topic | Box |"]
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for i in rows:
        lines.append(
            f"| {_cell(i.term)} | {_cell(i.meaning)} | {_cell(i.example)} | "
            f"{_cell(i.language)} | {_cell(i.topic)} | {i.box} |"
        )
    return "\n".join(lines) + "\n"


def render_reading_log(logs: Sequence[ReadingLog]) -> str:
    rows = sorted(logs, key=lambda r: (r.read_on, r.created_at), reverse=True)[:MAX_READING_ROWS]
    updated = max((r.created_at for r in logs), default=None)
    created = min((r.created_at for r in logs), default=None)
    head = front_matter(
        id=READING_ID,
        kind="reading",
        tags=["reading"],
        created=_iso(created) if created else "",
        updated=_iso(updated) if updated else "",
    )
    lines = [head, "# Reading log", "", "| Date | Reference | Reflection |", "| --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r.read_on.isoformat()} | {_cell(r.reference)} | {_cell(r.reflection)} |")
    return "\n".join(lines) + "\n"


def _single_line(text: str) -> str:
    return re.sub(r"\s+", " ", _CONTROL.sub(" ", text)).strip()


# -- layout -> DriveObject ---------------------------------------------------------------

MD_MIME = "text/markdown"


def note_object(note: Note, timezone: str = "UTC") -> DriveObject:
    year, month = _year_month(_local(note.created_at, timezone).date())
    name = f"{slugify(note.title)}-{note.id[:8]}.md"
    return DriveObject(
        "note",
        note.id,
        note.title.strip() or "Untitled",
        ("Notes", year, month),
        name,
        render_note(note).encode("utf-8"),
        MD_MIME,
    )


def diary_object(note: Note, timezone: str = "UTC") -> DriveObject:
    day = note.entry_date or _local(note.created_at, timezone).date()
    year, month = _year_month(day)
    return DriveObject(
        "diary",
        note.id,
        f"Diary {day.isoformat()}",
        ("Diary", year, month),
        f"{day.isoformat()}.md",
        render_diary(note).encode("utf-8"),
        MD_MIME,
    )


def daily_object(
    day: date,
    tasks: Sequence[Task],
    summary: DaySummary,
    *,
    readings: Sequence[ReadingLog] = (),
    reviewed: int = 0,
) -> DriveObject:
    year, month = _year_month(day)
    return DriveObject(
        "daily",
        day.isoformat(),
        f"Day {day.isoformat()}",
        ("Daily", year, month),
        f"{day.isoformat()}-summary.md",
        render_daily(day, tasks, summary, readings=readings, reviewed=reviewed).encode("utf-8"),
        MD_MIME,
    )


def vocabulary_object(items: Sequence[LearnItem]) -> DriveObject:
    return DriveObject(
        "learning",
        VOCABULARY_ID,
        "Vocabulary",
        ("Learning",),
        "vocabulary.md",
        render_vocabulary(items).encode("utf-8"),
        MD_MIME,
    )


def reading_object(logs: Sequence[ReadingLog]) -> DriveObject:
    return DriveObject(
        "reading",
        READING_ID,
        "Reading log",
        ("Reading",),
        "reading-log.md",
        render_reading_log(logs).encode("utf-8"),
        MD_MIME,
    )


def file_object(item: FileItem, content: bytes, timezone: str = "UTC") -> DriveObject:
    year, month = _year_month(_local(item.created_at, timezone).date())
    return DriveObject(
        "file",
        item.id,
        item.name,
        ("Files", year, month),
        safe_filename(item.name),
        content,
        item.mime,
    )


def file_meta_hash(item: FileItem, timezone: str = "UTC") -> str:
    """Hash of everything that decides a file's Drive copy, without loading the bytes."""
    year, month = _year_month(_local(item.created_at, timezone).date())
    payload = json.dumps(
        [item.id, item.mime, item.size, ["Files", year, month], safe_filename(item.name)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "DRIVE_FILE_SCOPE",
    "INCLUDE_KEYS",
    "MAX_BATCH",
    "OBJECT_TYPES",
    "ROOT_FOLDER",
    "DriveLink",
    "DriveObject",
    "SyncSettings",
    "content_hash",
    "daily_object",
    "diary_object",
    "file_meta_hash",
    "file_object",
    "front_matter",
    "is_safe_drive_name",
    "note_object",
    "reading_object",
    "render_daily",
    "render_diary",
    "render_note",
    "render_reading_log",
    "render_vocabulary",
    "safe_filename",
    "slugify",
    "vocabulary_object",
]
