"""Library files and the owner's profile photo, stored in the database (ADR 0034)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.life import (
    FILE_MIMES,
    FILE_TEXT_FOR_AGENT_MAX,
    MAX_FILE_BYTES,
    MAX_PHOTO_BYTES,
    OWNER_STORAGE_CAP_BYTES,
    PHOTO_MIMES,
    FileItem,
    LifeError,
    LifeTooLarge,
    LifeUnsupported,
    StoredPhoto,
    clean_file_name,
    clean_file_patch,
    clean_tags,
    clean_text,
    file_kind,
    magic_matches,
    normalize_mime,
    page_args,
)
from personal_agent.domain.ports import FileRepository, ProfilePhotoRepository

STORAGE_FULL = "Storage limit reached."


def decode_payload(data_base64: Any, max_bytes: int, *, label: str = "file") -> bytes:
    """Decode base64 JSON content, refusing oversize input before allocating the bytes."""
    if not isinstance(data_base64, str) or not data_base64:
        raise LifeError("data_base64 is required.")
    if len(data_base64) > (max_bytes * 4) // 3 + 8:
        raise LifeTooLarge(f"The {label} is larger than {max_bytes // (1024 * 1024) or 1} MB.")
    try:
        content = base64.b64decode(data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LifeError("data_base64 is not valid base64.") from exc
    if len(content) > max_bytes:
        raise LifeTooLarge(f"The {label} is larger than {max_bytes // (1024 * 1024) or 1} MB.")
    if not content:
        raise LifeError("The upload is empty.")
    return content


class FileService:
    def __init__(
        self,
        repository: FileRepository,
        ctx: LifeContext,
        *,
        max_file_bytes: int = MAX_FILE_BYTES,
        owner_cap_bytes: int = OWNER_STORAGE_CAP_BYTES,
    ) -> None:
        self._repo = repository
        self._ctx = ctx
        self._max_file = max_file_bytes
        self._cap = owner_cap_bytes

    def upload(self, owner: str, data: Mapping[str, Any]) -> FileItem:
        name = clean_file_name(data.get("name"))
        mime = normalize_mime(data.get("mime"))
        if mime not in FILE_MIMES:
            raise LifeUnsupported(f"Files of type '{mime}' are not allowed.")
        content = decode_payload(data.get("data_base64"), self._max_file)
        if not magic_matches(mime, content):
            raise LifeUnsupported("The file content does not match its declared type.")
        _, _, used = self._repo.stats(owner)
        if used + len(content) > self._cap:
            raise LifeTooLarge(STORAGE_FULL)
        item = FileItem(
            id=uuid.uuid4().hex,
            owner_user_id=owner,
            name=name,
            mime=mime,
            size=len(content),
            kind=file_kind(mime),
            description=clean_text(data, "description", 500),
            tags=clean_tags(data.get("tags")),
            created_at=self._ctx.now(),
        )
        self._repo.add(item, content)
        self._ctx.record("file.uploaded", owner, id=item.id, mime=mime, size=item.size)
        return item

    def get(self, owner: str, file_id: str) -> FileItem:
        item = self._repo.get(owner, file_id)
        if item is None:
            raise not_found("File")
        return item

    def content(self, owner: str, file_id: str) -> tuple[FileItem, bytes]:
        found = self._repo.get_content(owner, file_id)
        if found is None:
            raise not_found("File")
        return found

    def update(self, owner: str, file_id: str, data: Mapping[str, Any]) -> FileItem:
        item = self.get(owner, file_id)
        changes = clean_file_patch(data)
        for key, value in changes.items():
            setattr(item, key, value)
        if changes:
            self._repo.save(item)
            self._ctx.record("file.updated", owner, id=item.id, fields=sorted(changes))
        return item

    def delete(self, owner: str, file_id: str) -> None:
        if not self._repo.delete(owner, file_id):
            raise not_found("File")
        self._ctx.record("file.deleted", owner, id=file_id)

    def list(
        self,
        owner: str,
        *,
        kind: str | None = None,
        q: str = "",
        tag: str = "",
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[FileItem]:
        if kind not in (None, "file", "image"):
            raise LifeError("kind must be 'file' or 'image'.")
        lim, off = page_args(limit, offset)
        return self._repo.list(
            owner, kind=kind, q=q.strip(), tag=tag.strip().lower(), limit=lim, offset=off
        )

    def stats(self, owner: str) -> dict[str, int]:
        files, images, total = self._repo.stats(owner)
        return {"files": files, "images": images, "bytes": total}

    def search_for_agent(
        self, owner: str, query: str, kind: str | None, limit: int
    ) -> Sequence[tuple[FileItem, str | None]]:
        """Metadata plus (for text files) the first 20 000 chars; callers must wrap as untrusted."""
        items = self.list(owner, kind=kind, q=query, limit=max(1, min(limit, 10)))
        out: list[tuple[FileItem, str | None]] = []
        for item in items:
            text: str | None = None
            if item.mime.startswith("text/") or item.mime == "application/json":
                found = self._repo.get_content(owner, item.id)
                if found is not None:
                    text = found[1].decode("utf-8", errors="replace")[:FILE_TEXT_FOR_AGENT_MAX]
            out.append((item, text))
        return out


class ProfilePhotoService:
    def __init__(self, repository: ProfilePhotoRepository, ctx: LifeContext) -> None:
        self._repo = repository
        self._ctx = ctx

    def put(self, owner: str, data: Mapping[str, Any]) -> None:
        mime = normalize_mime(data.get("mime"))
        if mime not in PHOTO_MIMES:
            raise LifeUnsupported("The photo must be a PNG, JPEG or WebP image.")
        content = decode_payload(data.get("data_base64"), MAX_PHOTO_BYTES, label="photo")
        if not magic_matches(mime, content):
            raise LifeUnsupported("The photo content does not match its declared type.")
        self._repo.put(
            owner,
            StoredPhoto(
                mime=mime,
                content=content,
                etag=hashlib.sha256(content).hexdigest()[:32],
                updated_at=self._ctx.now(),
            ),
        )
        self._ctx.record("profile.photo_set", owner, mime=mime, size=len(content))

    def get(self, owner: str) -> StoredPhoto | None:
        return self._repo.get(owner)

    def has_photo(self, owner: str) -> bool:
        return self._repo.exists(owner)

    def delete(self, owner: str) -> None:
        if self._repo.delete(owner):
            self._ctx.record("profile.photo_removed", owner)
