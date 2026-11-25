"""SQLAlchemy repositories for the life modules (SQLite and Postgres)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, defer, sessionmaker

from personal_agent.domain.life import (
    FileItem,
    LearnItem,
    LifeConflict,
    Note,
    ReadingLog,
    ReadingPlan,
    StoredPhoto,
)
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import (
    FileRow,
    LearnItemRow,
    LearnReviewRow,
    NoteRow,
    ProfilePhotoRow,
    ReadingLogRow,
    ReadingPlanRow,
)


def _aware(value: datetime) -> datetime:
    """SQLite drops tzinfo; every stored timestamp is UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _contains(column: Any, text: str) -> Any:
    return func.lower(column).contains(text.lower(), autoescape=True)


# -- notes ---------------------------------------------------------------------------------


def _note(row: NoteRow) -> Note:
    return Note(
        id=row.id,
        owner_user_id=row.owner_user_id,
        kind=row.kind,
        title=row.title or "",
        body=row.body or "",
        tags=list(row.tags or []),
        mood=row.mood,
        entry_date=row.entry_date,
        pinned=bool(row.pinned),
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
    )


def _apply_note(row: NoteRow, note: Note) -> None:
    row.kind = note.kind
    row.title = note.title
    row.body = note.body
    row.tags = list(note.tags)
    row.mood = note.mood
    row.entry_date = note.entry_date
    row.pinned = note.pinned
    row.updated_at = note.updated_at


class NoteRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, note: Note) -> None:
        row = NoteRow(id=note.id, owner_user_id=note.owner_user_id, created_at=note.created_at)
        _apply_note(row, note)
        try:
            with session_scope(self._factory) as session:
                session.add(row)
        except IntegrityError as exc:
            raise LifeConflict("A diary entry for this date already exists.") from exc

    def get(self, owner_user_id: str, note_id: str) -> Note | None:
        with session_scope(self._factory) as session:
            row = session.get(NoteRow, note_id)
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _note(row)

    def save(self, note: Note) -> None:
        try:
            with session_scope(self._factory) as session:
                row = session.get(NoteRow, note.id)
                if row is not None and row.owner_user_id == note.owner_user_id:
                    _apply_note(row, note)
        except IntegrityError as exc:
            raise LifeConflict("A diary entry for this date already exists.") from exc

    def delete(self, owner_user_id: str, note_id: str) -> bool:
        with session_scope(self._factory) as session:
            row = session.get(NoteRow, note_id)
            if row is None or row.owner_user_id != owner_user_id:
                return False
            session.delete(row)
            return True

    def list(
        self,
        owner_user_id: str,
        *,
        kind: str | None,
        q: str,
        tag: str,
        limit: int,
        offset: int,
    ) -> list[Note]:
        with session_scope(self._factory) as session:
            query = session.query(NoteRow).filter(NoteRow.owner_user_id == owner_user_id)
            if kind:
                query = query.filter(NoteRow.kind == kind)
            if q:
                query = query.filter(or_(_contains(NoteRow.title, q), _contains(NoteRow.body, q)))
            if kind == "diary":
                query = query.order_by(NoteRow.entry_date.desc(), NoteRow.created_at.desc())
            else:
                query = query.order_by(
                    NoteRow.pinned.desc(), NoteRow.created_at.desc(), NoteRow.id.desc()
                )
            if tag:
                notes = [_note(r) for r in query.all() if tag in (r.tags or [])]
                return notes[offset : offset + limit]
            return [_note(r) for r in query.offset(offset).limit(limit).all()]

    def find_diary(self, owner_user_id: str, entry_date: date) -> Note | None:
        with session_scope(self._factory) as session:
            row = (
                session.query(NoteRow)
                .filter(
                    NoteRow.owner_user_id == owner_user_id,
                    NoteRow.kind == "diary",
                    NoteRow.entry_date == entry_date,
                )
                .first()
            )
            return _note(row) if row else None

    def count(self, owner_user_id: str, kind: str) -> int:
        with session_scope(self._factory) as session:
            return (
                session.query(func.count(NoteRow.id))
                .filter(NoteRow.owner_user_id == owner_user_id, NoteRow.kind == kind)
                .scalar()
                or 0
            )

    def diary_dates(self, owner_user_id: str) -> list[date]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(NoteRow.entry_date)
                .filter(NoteRow.owner_user_id == owner_user_id, NoteRow.kind == "diary")
                .all()
            )
            return [r[0] for r in rows if r[0] is not None]

    def recent(self, owner_user_id: str, kind: str, limit: int) -> list[Note]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(NoteRow)
                .filter(NoteRow.owner_user_id == owner_user_id, NoteRow.kind == kind)
                .order_by(NoteRow.updated_at.desc(), NoteRow.id.desc())
                .limit(limit)
                .all()
            )
            return [_note(r) for r in rows]

    def delete_all(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            return int(
                session.query(NoteRow).filter(NoteRow.owner_user_id == owner_user_id).delete()
            )


# -- files ---------------------------------------------------------------------------------


def _file(row: FileRow) -> FileItem:
    return FileItem(
        id=row.id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        mime=row.mime,
        size=int(row.size or 0),
        kind=row.kind,
        description=row.description or "",
        tags=list(row.tags or []),
        created_at=_aware(row.created_at),
    )


class FileRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, item: FileItem, content: bytes) -> None:
        with session_scope(self._factory) as session:
            session.add(
                FileRow(
                    id=item.id,
                    owner_user_id=item.owner_user_id,
                    name=item.name,
                    mime=item.mime,
                    size=item.size,
                    kind=item.kind,
                    description=item.description,
                    tags=list(item.tags),
                    content=content,
                    created_at=item.created_at,
                )
            )

    def get(self, owner_user_id: str, file_id: str) -> FileItem | None:
        with session_scope(self._factory) as session:
            row = session.get(FileRow, file_id, options=[defer(FileRow.content)])
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _file(row)

    def get_content(self, owner_user_id: str, file_id: str) -> tuple[FileItem, bytes] | None:
        with session_scope(self._factory) as session:
            row = session.get(FileRow, file_id)
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _file(row), bytes(row.content)

    def save(self, item: FileItem) -> None:
        with session_scope(self._factory) as session:
            row = session.get(FileRow, item.id)
            if row is not None and row.owner_user_id == item.owner_user_id:
                row.name = item.name
                row.description = item.description
                row.tags = list(item.tags)

    def delete(self, owner_user_id: str, file_id: str) -> bool:
        with session_scope(self._factory) as session:
            row = session.get(FileRow, file_id)
            if row is None or row.owner_user_id != owner_user_id:
                return False
            session.delete(row)
            return True

    def list(
        self,
        owner_user_id: str,
        *,
        kind: str | None,
        q: str,
        tag: str,
        limit: int,
        offset: int,
    ) -> list[FileItem]:
        with session_scope(self._factory) as session:
            query = (
                session.query(FileRow)
                .options(defer(FileRow.content))
                .filter(FileRow.owner_user_id == owner_user_id)
            )
            if kind:
                query = query.filter(FileRow.kind == kind)
            if q:
                query = query.filter(
                    or_(_contains(FileRow.name, q), _contains(FileRow.description, q))
                )
            query = query.order_by(FileRow.created_at.desc(), FileRow.id.desc())
            if tag:
                items = [_file(r) for r in query.all() if tag in (r.tags or [])]
                return items[offset : offset + limit]
            return [_file(r) for r in query.offset(offset).limit(limit).all()]

    def stats(self, owner_user_id: str) -> tuple[int, int, int]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(
                    FileRow.kind, func.count(FileRow.id), func.coalesce(func.sum(FileRow.size), 0)
                )
                .filter(FileRow.owner_user_id == owner_user_id)
                .group_by(FileRow.kind)
                .all()
            )
            files = images = total = 0
            for kind, count, size in rows:
                total += int(size)
                if kind == "image":
                    images += int(count)
                else:
                    files += int(count)
            return files, images, total

    def delete_all(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            return int(
                session.query(FileRow).filter(FileRow.owner_user_id == owner_user_id).delete()
            )


class ProfilePhotoRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get(self, owner_user_id: str) -> StoredPhoto | None:
        with session_scope(self._factory) as session:
            row = session.get(ProfilePhotoRow, owner_user_id)
            if row is None:
                return None
            return StoredPhoto(
                mime=row.mime,
                content=bytes(row.content),
                etag=row.etag,
                updated_at=_aware(row.updated_at),
            )

    def put(self, owner_user_id: str, photo: StoredPhoto) -> None:
        with session_scope(self._factory) as session:
            row = session.get(ProfilePhotoRow, owner_user_id)
            if row is None:
                row = ProfilePhotoRow(owner_user_id=owner_user_id)
                session.add(row)
            row.mime = photo.mime
            row.content = photo.content
            row.etag = photo.etag
            row.updated_at = photo.updated_at

    def delete(self, owner_user_id: str) -> bool:
        with session_scope(self._factory) as session:
            row = session.get(ProfilePhotoRow, owner_user_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def exists(self, owner_user_id: str) -> bool:
        with session_scope(self._factory) as session:
            return session.get(ProfilePhotoRow, owner_user_id) is not None


# -- learning ------------------------------------------------------------------------------


def _learn(row: LearnItemRow) -> LearnItem:
    return LearnItem(
        id=row.id,
        owner_user_id=row.owner_user_id,
        kind=row.kind,
        term=row.term,
        meaning=row.meaning or "",
        example=row.example or "",
        language=row.language,
        topic=row.topic or "",
        box=int(row.box or 0),
        next_review_at=_aware(row.next_review_at),
        times_correct=int(row.times_correct or 0),
        times_wrong=int(row.times_wrong or 0),
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
    )


def _apply_learn(row: LearnItemRow, item: LearnItem) -> None:
    row.kind = item.kind
    row.term = item.term
    row.term_key = item.term.casefold()
    row.meaning = item.meaning
    row.example = item.example
    row.language = item.language
    row.topic = item.topic
    row.box = item.box
    row.next_review_at = item.next_review_at
    row.times_correct = item.times_correct
    row.times_wrong = item.times_wrong
    row.updated_at = item.updated_at


class LearnRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, item: LearnItem) -> None:
        row = LearnItemRow(id=item.id, owner_user_id=item.owner_user_id, created_at=item.created_at)
        _apply_learn(row, item)
        try:
            with session_scope(self._factory) as session:
                session.add(row)
        except IntegrityError as exc:
            raise LifeConflict("This term is already in your list.") from exc

    def get(self, owner_user_id: str, item_id: str) -> LearnItem | None:
        with session_scope(self._factory) as session:
            row = session.get(LearnItemRow, item_id)
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _learn(row)

    def save(self, item: LearnItem) -> None:
        try:
            with session_scope(self._factory) as session:
                row = session.get(LearnItemRow, item.id)
                if row is not None and row.owner_user_id == item.owner_user_id:
                    _apply_learn(row, item)
        except IntegrityError as exc:
            raise LifeConflict("This term is already in your list.") from exc

    def delete(self, owner_user_id: str, item_id: str) -> bool:
        with session_scope(self._factory) as session:
            row = session.get(LearnItemRow, item_id)
            if row is None or row.owner_user_id != owner_user_id:
                return False
            session.delete(row)
            return True

    def list(
        self,
        owner_user_id: str,
        *,
        q: str,
        topic: str,
        language: str,
        due_at: datetime | None,
        limit: int,
        offset: int,
        due_first: bool = False,
    ) -> list[LearnItem]:
        with session_scope(self._factory) as session:
            query = session.query(LearnItemRow).filter(LearnItemRow.owner_user_id == owner_user_id)
            if q:
                query = query.filter(
                    or_(
                        _contains(LearnItemRow.term, q),
                        _contains(LearnItemRow.meaning, q),
                        _contains(LearnItemRow.example, q),
                    )
                )
            if topic:
                query = query.filter(LearnItemRow.topic == topic)
            if language:
                query = query.filter(LearnItemRow.language == language)
            if due_at is not None:
                query = query.filter(LearnItemRow.next_review_at <= due_at)
            if due_first:
                query = query.order_by(LearnItemRow.next_review_at.asc(), LearnItemRow.id.asc())
            else:
                query = query.order_by(LearnItemRow.created_at.desc(), LearnItemRow.id.desc())
            return [_learn(r) for r in query.offset(offset).limit(limit).all()]

    def find_term(self, owner_user_id: str, term: str, language: str) -> LearnItem | None:
        with session_scope(self._factory) as session:
            row = (
                session.query(LearnItemRow)
                .filter(
                    LearnItemRow.owner_user_id == owner_user_id,
                    LearnItemRow.language == language,
                    LearnItemRow.term_key == term.casefold(),
                )
                .first()
            )
            return _learn(row) if row else None

    def counts(self, owner_user_id: str, now: datetime) -> tuple[int, int, int]:
        with session_scope(self._factory) as session:
            base = session.query(func.count(LearnItemRow.id)).filter(
                LearnItemRow.owner_user_id == owner_user_id
            )
            total = base.scalar() or 0
            due = base.filter(LearnItemRow.next_review_at <= now).scalar() or 0
            learned = base.filter(LearnItemRow.box >= 3).scalar() or 0
            return int(total), int(due), int(learned)

    def topics(self, owner_user_id: str) -> list[str]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(LearnItemRow.topic)
                .filter(LearnItemRow.owner_user_id == owner_user_id, LearnItemRow.topic != "")
                .distinct()
                .order_by(LearnItemRow.topic)
                .all()
            )
            return [r[0] for r in rows]

    def add_review(
        self, owner_user_id: str, item_id: str, result: str, reviewed_at: datetime
    ) -> None:
        import uuid

        with session_scope(self._factory) as session:
            session.add(
                LearnReviewRow(
                    id=uuid.uuid4().hex,
                    owner_user_id=owner_user_id,
                    item_id=item_id,
                    result=result,
                    reviewed_at=reviewed_at,
                )
            )

    def review_times(self, owner_user_id: str) -> list[datetime]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(LearnReviewRow.reviewed_at)
                .filter(LearnReviewRow.owner_user_id == owner_user_id)
                .all()
            )
            return [_aware(r[0]) for r in rows]

    def all_reviews(self, owner_user_id: str) -> list[dict[str, Any]]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(LearnReviewRow)
                .filter(LearnReviewRow.owner_user_id == owner_user_id)
                .order_by(LearnReviewRow.reviewed_at)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "item_id": r.item_id,
                    "result": r.result,
                    "reviewed_at": _aware(r.reviewed_at).isoformat(),
                }
                for r in rows
            ]

    def delete_all(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            session.query(LearnReviewRow).filter(
                LearnReviewRow.owner_user_id == owner_user_id
            ).delete()
            return int(
                session.query(LearnItemRow)
                .filter(LearnItemRow.owner_user_id == owner_user_id)
                .delete()
            )


# -- reading -------------------------------------------------------------------------------


def _plan(row: ReadingPlanRow) -> ReadingPlan:
    return ReadingPlan(
        id=row.id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        items=list(row.items or []),
        position=int(row.position or 0),
        active=bool(row.active),
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
    )


def _log(row: ReadingLogRow) -> ReadingLog:
    return ReadingLog(
        id=row.id,
        owner_user_id=row.owner_user_id,
        reference=row.reference,
        read_on=row.read_on,
        reflection=row.reflection or "",
        plan_id=row.plan_id,
        created_at=_aware(row.created_at),
    )


class ReadingRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add_plan(self, plan: ReadingPlan) -> None:
        with session_scope(self._factory) as session:
            session.add(
                ReadingPlanRow(
                    id=plan.id,
                    owner_user_id=plan.owner_user_id,
                    name=plan.name,
                    items=list(plan.items),
                    position=plan.position,
                    active=plan.active,
                    created_at=plan.created_at,
                    updated_at=plan.updated_at,
                )
            )

    def get_plan(self, owner_user_id: str, plan_id: str) -> ReadingPlan | None:
        with session_scope(self._factory) as session:
            row = session.get(ReadingPlanRow, plan_id)
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _plan(row)

    def save_plan(self, plan: ReadingPlan) -> None:
        with session_scope(self._factory) as session:
            row = session.get(ReadingPlanRow, plan.id)
            if row is not None and row.owner_user_id == plan.owner_user_id:
                row.name = plan.name
                row.items = list(plan.items)
                row.position = plan.position
                row.active = plan.active
                row.updated_at = plan.updated_at

    def delete_plan(self, owner_user_id: str, plan_id: str) -> bool:
        with session_scope(self._factory) as session:
            row = session.get(ReadingPlanRow, plan_id)
            if row is None or row.owner_user_id != owner_user_id:
                return False
            session.query(ReadingLogRow).filter(ReadingLogRow.plan_id == plan_id).update(
                {ReadingLogRow.plan_id: None}
            )
            session.delete(row)
            return True

    def list_plans(self, owner_user_id: str, *, limit: int, offset: int) -> list[ReadingPlan]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(ReadingPlanRow)
                .filter(ReadingPlanRow.owner_user_id == owner_user_id)
                .order_by(ReadingPlanRow.created_at.desc(), ReadingPlanRow.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [_plan(r) for r in rows]

    def add_log(self, log: ReadingLog) -> None:
        with session_scope(self._factory) as session:
            session.add(
                ReadingLogRow(
                    id=log.id,
                    owner_user_id=log.owner_user_id,
                    reference=log.reference,
                    read_on=log.read_on,
                    reflection=log.reflection,
                    plan_id=log.plan_id,
                    created_at=log.created_at,
                )
            )

    def get_log(self, owner_user_id: str, log_id: str) -> ReadingLog | None:
        with session_scope(self._factory) as session:
            row = session.get(ReadingLogRow, log_id)
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _log(row)

    def save_log(self, log: ReadingLog) -> None:
        with session_scope(self._factory) as session:
            row = session.get(ReadingLogRow, log.id)
            if row is not None and row.owner_user_id == log.owner_user_id:
                row.reference = log.reference
                row.read_on = log.read_on
                row.reflection = log.reflection

    def delete_log(self, owner_user_id: str, log_id: str) -> bool:
        with session_scope(self._factory) as session:
            row = session.get(ReadingLogRow, log_id)
            if row is None or row.owner_user_id != owner_user_id:
                return False
            session.delete(row)
            return True

    def list_logs(
        self, owner_user_id: str, *, plan_id: str, limit: int, offset: int
    ) -> list[ReadingLog]:
        with session_scope(self._factory) as session:
            query = session.query(ReadingLogRow).filter(
                ReadingLogRow.owner_user_id == owner_user_id
            )
            if plan_id:
                query = query.filter(ReadingLogRow.plan_id == plan_id)
            rows = (
                query.order_by(ReadingLogRow.created_at.desc(), ReadingLogRow.id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [_log(r) for r in rows]

    def log_count(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            return (
                session.query(func.count(ReadingLogRow.id))
                .filter(ReadingLogRow.owner_user_id == owner_user_id)
                .scalar()
                or 0
            )

    def log_dates(self, owner_user_id: str) -> list[date]:
        with session_scope(self._factory) as session:
            rows = (
                session.query(ReadingLogRow.read_on)
                .filter(ReadingLogRow.owner_user_id == owner_user_id)
                .distinct()
                .all()
            )
            return [r[0] for r in rows]

    def delete_all(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            session.query(ReadingLogRow).filter(
                ReadingLogRow.owner_user_id == owner_user_id
            ).delete()
            return int(
                session.query(ReadingPlanRow)
                .filter(ReadingPlanRow.owner_user_id == owner_user_id)
                .delete()
            )
