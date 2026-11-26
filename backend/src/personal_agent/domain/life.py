"""Life modules (notes, diary, files, learning, reading): pure rules, no I/O.

The API contract lives in docs/LIFE_API_CONTRACT.md. Everything here is validation,
Leitner scheduling, streak maths and reading-plan templates, so it can be unit tested
without a database.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from personal_agent.domain.exceptions import AgentError

# -- errors (the web layer maps each subclass to a status code) ------------------------


class LifeError(AgentError):
    """Invalid input (400)."""

    status_code = 400


class LifeNotFound(LifeError):
    status_code = 404


class LifeConflict(LifeError):
    status_code = 409


class LifeTooLarge(LifeError):
    status_code = 413


class LifeUnsupported(LifeError):
    status_code = 415


# -- limits -----------------------------------------------------------------------------

NOTE_KINDS = ("note", "diary")
MOODS = ("great", "good", "okay", "low", "bad")
NOTE_TITLE_MAX = 200
NOTE_BODY_MAX = 50_000
TAGS_MAX = 10
TAG_MAX = 30

MAX_FILE_BYTES = 5 * 1024 * 1024
OWNER_STORAGE_CAP_BYTES = 200 * 1024 * 1024
MAX_PHOTO_BYTES = 1024 * 1024
FILE_NAME_MAX = 255
FILE_DESCRIPTION_MAX = 500
FILE_TEXT_FOR_AGENT_MAX = 20_000
FILE_MIMES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
    }
)
PHOTO_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
INLINE_MIMES = frozenset({"application/pdf"})  # images are inline too

LEARN_KINDS = ("word", "phrase", "fact")
LEARN_TERM_MAX = 200
LEARN_TEXT_MAX = 1000
LEARN_TOPIC_MAX = 60
LEARN_BATCH_MAX = 20
LEITNER_MAX_BOX = 5
LEITNER_INTERVALS: Mapping[int, timedelta] = {
    0: timedelta(minutes=10),
    1: timedelta(days=1),
    2: timedelta(days=3),
    3: timedelta(days=7),
    4: timedelta(days=14),
    5: timedelta(days=30),
}
LEARNED_BOX = 3

READING_NAME_MAX = 120
READING_ITEMS_MAX = 1500
READING_REFERENCE_MAX = 120
READING_REFLECTION_MAX = 5000

BIO_MAX = 500

PAGE_DEFAULT = 50
PAGE_MAX = 200

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# -- entities ---------------------------------------------------------------------------


@dataclass(slots=True)
class Note:
    id: str
    owner_user_id: str
    kind: str
    title: str
    body: str
    tags: list[str]
    mood: str | None
    entry_date: date | None
    pinned: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FileItem:
    id: str
    owner_user_id: str
    name: str
    mime: str
    size: int
    kind: str  # "file" | "image"
    description: str
    tags: list[str]
    created_at: datetime


@dataclass(slots=True)
class LearnItem:
    id: str
    owner_user_id: str
    kind: str
    term: str
    meaning: str
    example: str
    language: str
    topic: str
    box: int
    next_review_at: datetime
    times_correct: int
    times_wrong: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ReadingPlan:
    id: str
    owner_user_id: str
    name: str
    items: list[str]
    position: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @property
    def next(self) -> str | None:
        return self.items[self.position] if 0 <= self.position < len(self.items) else None

    @property
    def progress(self) -> float:
        if not self.items:
            return 0.0
        return min(1.0, max(0.0, self.position / len(self.items)))


@dataclass(slots=True)
class ReadingLog:
    id: str
    owner_user_id: str
    reference: str
    read_on: date
    reflection: str
    plan_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NotificationPolicy:
    """Delivery rules the scheduler consults before any proactive external send."""

    in_app: bool = True
    telegram: bool = True
    reminders: bool = True
    quiet_enabled: bool = False
    quiet_start: str = "22:00"
    quiet_end: str = "07:00"

    @classmethod
    def from_stored(cls, stored: Mapping[str, Any] | None) -> NotificationPolicy:
        data = stored or {}
        channels = data.get("channels") or {}
        quiet = data.get("quiet_hours") or {}
        return cls(
            in_app=bool(channels.get("in_app", True)),
            telegram=bool(channels.get("telegram", True)),
            reminders=bool(data.get("reminders", True)),
            quiet_enabled=bool(quiet.get("enabled", False)),
            quiet_start=str(quiet.get("start") or "22:00"),
            quiet_end=str(quiet.get("end") or "07:00"),
        )


@dataclass(slots=True)
class StoredPhoto:
    mime: str
    content: bytes
    etag: str
    updated_at: datetime


# -- generic field helpers ---------------------------------------------------------------


def page_args(limit: int | None, offset: int | None) -> tuple[int, int]:
    lim = PAGE_DEFAULT if limit is None else limit
    off = 0 if offset is None else offset
    if not 1 <= lim <= PAGE_MAX:
        raise LifeError(f"limit must be between 1 and {PAGE_MAX}.")
    if off < 0:
        raise LifeError("offset must be 0 or more.")
    return lim, off


def clean_text(data: Mapping[str, Any], key: str, max_len: int, *, strip: bool = True) -> str:
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise LifeError(f"{key} must be a string.")
    value = value.strip() if strip else value
    if len(value) > max_len:
        raise LifeError(f"{key} must be at most {max_len} characters.")
    return value


def _flag(data: Mapping[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise LifeError(f"{key} must be true or false.")
    return value


def clean_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
        raise LifeError("tags must be a list of strings.")
    tags: list[str] = []
    for raw in value:
        tag = raw.strip().lower()
        if not tag:
            continue
        if len(tag) > TAG_MAX:
            raise LifeError(f"Each tag must be at most {TAG_MAX} characters.")
        if tag not in tags:
            tags.append(tag)
    if len(tags) > TAGS_MAX:
        raise LifeError(f"At most {TAGS_MAX} tags are allowed.")
    return tags


def parse_date(value: Any, field_name: str = "date") -> date:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise LifeError(f"{field_name} must be YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LifeError(f"{field_name} is not a valid date.") from exc


def valid_hhmm(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise LifeError(f"{field_name} must be HH:MM.")
    return value


def streak_days(days: set[date] | frozenset[date], today: date) -> int:
    """Consecutive days ending today, or yesterday when today is not recorded yet."""
    if today in days:
        cursor = today
    elif (today - timedelta(days=1)) in days:
        cursor = today - timedelta(days=1)
    else:
        return 0
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


# -- notes and diary ----------------------------------------------------------------------


def _derive_title(body: str) -> str:
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:60]
    return ""


def clean_note_create(data: Mapping[str, Any], *, today: date) -> dict[str, Any]:
    kind = data.get("kind")
    if kind not in NOTE_KINDS:
        raise LifeError("kind must be 'note' or 'diary'.")
    title = clean_text(data, "title", NOTE_TITLE_MAX)
    body = clean_text(data, "body", NOTE_BODY_MAX, strip=False)
    if not title and not body.strip():
        raise LifeError("A note needs a title or a body.")
    mood = data.get("mood")
    entry_date: date | None = None
    if kind == "diary":
        if mood is not None and mood not in MOODS:
            raise LifeError(f"mood must be one of: {', '.join(MOODS)}.")
        raw_date = data.get("entry_date")
        entry_date = today if raw_date is None else parse_date(raw_date, "entry_date")
    else:
        if mood is not None:
            raise LifeError("mood is only for diary entries.")
        if data.get("entry_date") is not None:
            raise LifeError("entry_date is only for diary entries.")
        if not title:
            title = _derive_title(body)
    return {
        "kind": kind,
        "title": title,
        "body": body,
        "tags": clean_tags(data.get("tags")),
        "mood": mood,
        "entry_date": entry_date,
        "pinned": _flag(data, "pinned", False),
    }


def clean_note_patch(note: Note, data: Mapping[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if "title" in data:
        changes["title"] = clean_text(data, "title", NOTE_TITLE_MAX)
    if "body" in data:
        changes["body"] = clean_text(data, "body", NOTE_BODY_MAX, strip=False)
    if "tags" in data:
        changes["tags"] = clean_tags(data["tags"])
    if "pinned" in data:
        changes["pinned"] = _flag(data, "pinned", False)
    if "mood" in data:
        mood = data["mood"]
        if note.kind != "diary" and mood is not None:
            raise LifeError("mood is only for diary entries.")
        if mood is not None and mood not in MOODS:
            raise LifeError(f"mood must be one of: {', '.join(MOODS)}.")
        changes["mood"] = mood
    if "entry_date" in data:
        if note.kind != "diary":
            raise LifeError("entry_date is only for diary entries.")
        changes["entry_date"] = parse_date(data["entry_date"], "entry_date")
    title = changes.get("title", note.title)
    body = changes.get("body", note.body)
    if not title and not body.strip():
        raise LifeError("A note needs a title or a body.")
    return changes


# -- files ----------------------------------------------------------------------------------

_MAGIC: tuple[tuple[str, bytes], ...] = (
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/gif", b"GIF87a"),
    ("image/gif", b"GIF89a"),
    ("application/pdf", b"%PDF-"),
)


def normalize_mime(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifeError("mime is required.")
    return value.split(";", 1)[0].strip().lower()


def magic_matches(mime: str, content: bytes) -> bool:
    """Binary types must start with their signature; text types must not contain NUL bytes."""
    if mime == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    signatures = [sig for m, sig in _MAGIC if m == mime]
    if signatures:
        return any(content.startswith(sig) for sig in signatures)
    return b"\x00" not in content


def file_kind(mime: str) -> str:
    return "image" if mime.startswith("image/") else "file"


def is_inline(mime: str) -> bool:
    return mime.startswith("image/") or mime in INLINE_MIMES


def clean_file_name(value: Any) -> str:
    if not isinstance(value, str):
        raise LifeError("name is required.")
    name = re.sub(r"[\x00-\x1f\x7f]", "", value.replace("\\", "/").rsplit("/", 1)[-1]).strip()
    if not name:
        raise LifeError("name is required.")
    if len(name) > FILE_NAME_MAX:
        raise LifeError(f"name must be at most {FILE_NAME_MAX} characters.")
    return name


def clean_file_patch(data: Mapping[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if "name" in data:
        changes["name"] = clean_file_name(data["name"])
    if "description" in data:
        changes["description"] = clean_text(data, "description", FILE_DESCRIPTION_MAX)
    if "tags" in data:
        changes["tags"] = clean_tags(data["tags"])
    return changes


# -- learning ---------------------------------------------------------------------------------


def clean_learn_item(data: Mapping[str, Any], *, partial: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not partial or "term" in data:
        term = clean_text(data, "term", LEARN_TERM_MAX)
        if not term:
            raise LifeError("term is required.")
        out["term"] = term
    if not partial or "meaning" in data:
        meaning = clean_text(data, "meaning", LEARN_TEXT_MAX)
        if not meaning:
            raise LifeError("meaning is required.")
        out["meaning"] = meaning
    if not partial or "example" in data:
        out["example"] = clean_text(data, "example", LEARN_TEXT_MAX)
    if "kind" in data or not partial:
        kind = data.get("kind", "word")
        if kind not in LEARN_KINDS:
            raise LifeError(f"kind must be one of: {', '.join(LEARN_KINDS)}.")
        out["kind"] = kind
    if "language" in data or not partial:
        language = clean_text(data, "language", 16) or "en"
        if not re.match(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$", language):
            raise LifeError("language must look like 'en' or 'pt-BR'.")
        out["language"] = language
    if "topic" in data or not partial:
        out["topic"] = clean_text(data, "topic", LEARN_TOPIC_MAX)
    return out


def leitner_review(box: int, result: str, now: datetime) -> tuple[int, datetime]:
    """know: box+1 (max 5); again: box 0. The next review uses the new box's interval."""
    if result == "know":
        new_box = min(LEITNER_MAX_BOX, box + 1)
    elif result == "again":
        new_box = 0
    else:
        raise LifeError("result must be 'know' or 'again'.")
    return new_box, now + LEITNER_INTERVALS[new_box]


# -- reading ----------------------------------------------------------------------------------

_NT_BOOKS: tuple[tuple[str, int], ...] = (
    ("Matthew", 28),
    ("Mark", 16),
    ("Luke", 24),
    ("John", 21),
    ("Acts", 28),
    ("Romans", 16),
    ("1 Corinthians", 16),
    ("2 Corinthians", 13),
    ("Galatians", 6),
    ("Ephesians", 6),
    ("Philippians", 4),
    ("Colossians", 4),
    ("1 Thessalonians", 5),
    ("2 Thessalonians", 3),
    ("1 Timothy", 6),
    ("2 Timothy", 4),
    ("Titus", 3),
    ("Philemon", 1),
    ("Hebrews", 13),
    ("James", 5),
    ("1 Peter", 5),
    ("2 Peter", 3),
    ("1 John", 5),
    ("2 John", 1),
    ("3 John", 1),
    ("Jude", 1),
    ("Revelation", 22),
)


def _chapters(book: str, count: int) -> list[str]:
    return [f"{book} {n}" for n in range(1, count + 1)]


def _numbered(label: str, count: int) -> list[str]:
    return [f"{label} {n}" for n in range(1, count + 1)]


def _new_testament_90() -> list[str]:
    chapters = [(book, n) for book, count in _NT_BOOKS for n in range(1, count + 1)]
    total, days = len(chapters), 90
    refs: list[str] = []
    for day in range(days):
        chunk = chapters[day * total // days : (day + 1) * total // days]
        parts: list[str] = []
        for book in dict.fromkeys(b for b, _ in chunk):
            nums = [n for b, n in chunk if b == book]
            parts.append(f"{book} {nums[0]}" + (f"-{nums[-1]}" if len(nums) > 1 else ""))
        refs.append("; ".join(parts))
    return refs


@dataclass(frozen=True, slots=True)
class ReadingTemplate:
    id: str
    name: str
    description: str
    items: tuple[str, ...]


def reading_templates() -> dict[str, ReadingTemplate]:
    return {
        t.id: t
        for t in (
            ReadingTemplate(
                "gospel-of-john-21",
                "Gospel of John in 21 days",
                "One chapter of John per day.",
                tuple(_chapters("John", 21)),
            ),
            ReadingTemplate(
                "psalms-30",
                "Psalms, first 30",
                "One psalm per day for a month.",
                tuple(_chapters("Psalm", 30)),
            ),
            ReadingTemplate(
                "proverbs-31",
                "Proverbs in a month",
                "One chapter of Proverbs per day, 31 days.",
                tuple(_chapters("Proverbs", 31)),
            ),
            ReadingTemplate(
                "book-20-days",
                "A book in 20 days",
                "Split any book into 20 equal daily portions.",
                tuple(f"Part {n} of 20" for n in range(1, 21)),
            ),
            ReadingTemplate(
                "book-chapter-a-day",
                "A book, one chapter a day (30 chapters)",
                "Read one chapter each day; rename the plan to your book.",
                tuple(_numbered("Chapter", 30)),
            ),
            ReadingTemplate(
                "articles-weekly-12",
                "One article a week for 12 weeks",
                "A steady habit of reading one long article each week.",
                tuple(f"Article for week {n}" for n in range(1, 13)),
            ),
            ReadingTemplate(
                "new-testament-90",
                "New Testament in 90 days",
                "All 260 chapters in 90 daily portions of two to three chapters.",
                tuple(_new_testament_90()),
            ),
        )
    }


def clean_reading_items(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
        raise LifeError("items must be a list of strings.")
    items = [i.strip() for i in value if i.strip()]
    if len(items) > READING_ITEMS_MAX:
        raise LifeError(f"A plan can have at most {READING_ITEMS_MAX} items.")
    if any(len(i) > READING_REFERENCE_MAX for i in items):
        raise LifeError(f"Each reference must be at most {READING_REFERENCE_MAX} characters.")
    return items


def clean_reading_name(data: Mapping[str, Any]) -> str:
    name = clean_text(data, "name", READING_NAME_MAX)
    if not name:
        raise LifeError("name is required.")
    return name


def clean_reading_log(data: Mapping[str, Any], *, partial: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not partial or "reference" in data:
        reference = clean_text(data, "reference", READING_REFERENCE_MAX)
        if not reference:
            raise LifeError("reference is required.")
        out["reference"] = reference
    if "read_on" in data and data["read_on"] is not None:
        out["read_on"] = parse_date(data["read_on"], "read_on")
    if "reflection" in data:
        out["reflection"] = clean_text(data, "reflection", READING_REFLECTION_MAX)
    return out


def same_reference(a: str, b: str) -> bool:
    return re.sub(r"\s+", " ", a).strip().lower() == re.sub(r"\s+", " ", b).strip().lower()
