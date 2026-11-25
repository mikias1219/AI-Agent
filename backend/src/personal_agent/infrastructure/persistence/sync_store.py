"""SQLAlchemy stores for Drive links, the folder cache and sync settings (contract 8-9)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.drive_sync import DriveLink, SyncSettings
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import (
    DriveFolderRow,
    DriveLinkRow,
    SyncSettingsRow,
)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _link(row: DriveLinkRow) -> DriveLink:
    return DriveLink(
        id=row.id,
        owner_user_id=row.owner_user_id,
        object_type=row.object_type,
        object_id=row.object_id,
        drive_file_id=row.drive_file_id,
        drive_url=row.drive_url or "",
        content_hash=row.content_hash or "",
        synced_at=_aware(row.synced_at) or datetime.now(UTC),
        local_deleted_at=_aware(row.local_deleted_at),
    )


class DriveLinkStoreImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def _find(
        self, session: Session, owner: str, object_type: str, object_id: str
    ) -> DriveLinkRow | None:
        return (
            session.query(DriveLinkRow)
            .filter_by(owner_user_id=owner, object_type=object_type, object_id=object_id)
            .one_or_none()
        )

    def get(self, owner_user_id: str, object_type: str, object_id: str) -> DriveLink | None:
        with session_scope(self._factory) as session:
            row = self._find(session, owner_user_id, object_type, object_id)
            return _link(row) if row else None

    def put(self, link: DriveLink) -> None:
        with session_scope(self._factory) as session:
            row = self._find(session, link.owner_user_id, link.object_type, link.object_id)
            if row is None:
                row = DriveLinkRow(
                    id=link.id,
                    owner_user_id=link.owner_user_id,
                    object_type=link.object_type,
                    object_id=link.object_id,
                )
                session.add(row)
            row.drive_file_id = link.drive_file_id
            row.drive_url = link.drive_url
            row.content_hash = link.content_hash
            row.synced_at = link.synced_at
            row.local_deleted_at = link.local_deleted_at

    def list(
        self, owner_user_id: str, *, object_type: str | None, limit: int, offset: int
    ) -> list[DriveLink]:
        with session_scope(self._factory) as session:
            query = session.query(DriveLinkRow).filter_by(owner_user_id=owner_user_id)
            if object_type:
                query = query.filter_by(object_type=object_type)
            rows = (
                query.order_by(DriveLinkRow.synced_at.desc(), DriveLinkRow.id)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [_link(r) for r in rows]

    def for_objects(
        self, owner_user_id: str, object_types: Sequence[str], object_ids: Sequence[str]
    ) -> list[DriveLink]:
        if not object_ids:
            return []
        with session_scope(self._factory) as session:
            rows = (
                session.query(DriveLinkRow)
                .filter(
                    DriveLinkRow.owner_user_id == owner_user_id,
                    DriveLinkRow.object_type.in_(list(object_types)),
                    DriveLinkRow.object_id.in_(list(object_ids)),
                )
                .all()
            )
            return [_link(r) for r in rows]

    def mark_local_deleted(self, owner_user_id: str, object_type: str, object_id: str) -> None:
        with session_scope(self._factory) as session:
            row = self._find(session, owner_user_id, object_type, object_id)
            if row is not None and row.local_deleted_at is None:
                row.local_deleted_at = datetime.now(UTC)

    def get_folder(self, owner_user_id: str, path: str) -> tuple[str, str] | None:
        with session_scope(self._factory) as session:
            row = session.get(DriveFolderRow, (owner_user_id, path))
            return (row.folder_id, row.folder_url or "") if row else None

    def put_folder(self, owner_user_id: str, path: str, folder_id: str, url: str) -> None:
        with session_scope(self._factory) as session:
            row = session.get(DriveFolderRow, (owner_user_id, path))
            if row is None:
                row = DriveFolderRow(owner_user_id=owner_user_id, path=path, folder_id=folder_id)
                session.add(row)
            row.folder_id = folder_id
            row.folder_url = url

    def drop_folders(self, owner_user_id: str) -> None:
        with session_scope(self._factory) as session:
            session.query(DriveFolderRow).filter_by(owner_user_id=owner_user_id).delete()

    def delete_all(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            count = session.query(DriveLinkRow).filter_by(owner_user_id=owner_user_id).delete()
            session.query(DriveFolderRow).filter_by(owner_user_id=owner_user_id).delete()
            return int(count)


class SyncSettingsStoreImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def get(self, owner_user_id: str, service: str) -> SyncSettings:
        with session_scope(self._factory) as session:
            row = session.get(SyncSettingsRow, (owner_user_id, service))
            if row is None:
                return SyncSettings(owner_user_id=owner_user_id, service=service)
            return SyncSettings(
                owner_user_id=owner_user_id,
                service=service,
                enabled=bool(row.enabled),
                include={str(k): bool(v) for k, v in (row.include or {}).items()},
                last_sync_at=_aware(row.last_sync_at),
                last_error=row.last_error or "",
            )

    def save(self, settings: SyncSettings) -> None:
        with session_scope(self._factory) as session:
            row = session.get(SyncSettingsRow, (settings.owner_user_id, settings.service))
            if row is None:
                row = SyncSettingsRow(
                    owner_user_id=settings.owner_user_id, service=settings.service
                )
                session.add(row)
            row.enabled = settings.enabled
            row.include = dict(settings.include)
            row.last_sync_at = settings.last_sync_at
            row.last_error = settings.last_error[:500]

    def delete_all(self, owner_user_id: str) -> int:
        with session_scope(self._factory) as session:
            return int(
                session.query(SyncSettingsRow).filter_by(owner_user_id=owner_user_id).delete()
            )
