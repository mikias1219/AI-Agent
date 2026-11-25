"""Learning items with Leitner review (contract section 3)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.life import (
    LEARN_BATCH_MAX,
    LEARNED_BOX,
    LearnItem,
    LifeConflict,
    LifeError,
    clean_learn_item,
    leitner_review,
    page_args,
    streak_days,
)
from personal_agent.domain.ports import LearnRepository


class LearnService:
    def __init__(self, repository: LearnRepository, ctx: LifeContext) -> None:
        self._repo = repository
        self._ctx = ctx

    def create_many(
        self, owner: str, items: Sequence[Mapping[str, Any]], *, source: str = "owner"
    ) -> tuple[list[LearnItem], int]:
        """Create items; duplicates (term, case-insensitive, same language) are skipped.

        Returns (created, skipped). One invalid item rejects the whole batch.
        """
        if not items:
            raise LifeError("Send at least one item.")
        if len(items) > LEARN_BATCH_MAX:
            raise LifeError(f"At most {LEARN_BATCH_MAX} items per request.")
        cleaned = [clean_learn_item(i) for i in items]
        now = self._ctx.now()
        created: list[LearnItem] = []
        seen: set[tuple[str, str]] = set()
        for fields in cleaned:
            key = (fields["language"], fields["term"].casefold())
            if key in seen or self._repo.find_term(owner, fields["term"], fields["language"]):
                continue
            seen.add(key)
            item = LearnItem(
                id=uuid.uuid4().hex,
                owner_user_id=owner,
                box=0,
                next_review_at=now,
                times_correct=0,
                times_wrong=0,
                created_at=now,
                updated_at=now,
                **fields,
            )
            try:
                self._repo.add(item)
            except LifeConflict:
                continue  # raced with an identical term
            created.append(item)
        skipped = len(cleaned) - len(created)
        self._ctx.record("learn.created", owner, count=len(created), skipped=skipped, source=source)
        return created, skipped

    def get(self, owner: str, item_id: str) -> LearnItem:
        item = self._repo.get(owner, item_id)
        if item is None:
            raise not_found("Learning item")
        return item

    def update(self, owner: str, item_id: str, data: Mapping[str, Any]) -> LearnItem:
        item = self.get(owner, item_id)
        changes = clean_learn_item(data, partial=True)
        if "term" in changes or "language" in changes:
            term = changes.get("term", item.term)
            language = changes.get("language", item.language)
            twin = self._repo.find_term(owner, term, language)
            if twin is not None and twin.id != item.id:
                raise LifeConflict("This term is already in your list.")
        for key, value in changes.items():
            setattr(item, key, value)
        if changes:
            item.updated_at = self._ctx.now()
            self._repo.save(item)
            self._ctx.record("learn.updated", owner, id=item.id, fields=sorted(changes))
        return item

    def delete(self, owner: str, item_id: str) -> None:
        if not self._repo.delete(owner, item_id):
            raise not_found("Learning item")
        self._ctx.record("learn.deleted", owner, id=item_id)

    def list(
        self,
        owner: str,
        *,
        q: str = "",
        topic: str = "",
        language: str = "",
        due: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[LearnItem]:
        lim, off = page_args(limit, offset)
        return self._repo.list(
            owner,
            q=q.strip(),
            topic=topic.strip(),
            language=language.strip(),
            due_at=self._ctx.now() if due else None,
            limit=lim,
            offset=off,
        )

    def due(self, owner: str, limit: int = 10) -> Sequence[LearnItem]:
        """Most overdue first (for agent tools and nudges)."""
        return self._repo.list(
            owner,
            q="",
            topic="",
            language="",
            due_at=self._ctx.now(),
            limit=max(1, min(limit, 200)),
            offset=0,
            due_first=True,
        )

    def review(self, owner: str, item_id: str, result: str) -> LearnItem:
        item = self.get(owner, item_id)
        now = self._ctx.now()
        item.box, item.next_review_at = leitner_review(item.box, result, now)
        if result == "know":
            item.times_correct += 1
        else:
            item.times_wrong += 1
        item.updated_at = now
        self._repo.save(item)
        self._repo.add_review(owner, item.id, result, now)
        self._ctx.record("learn.reviewed", owner, id=item.id, result=result, box=item.box)
        return item

    def stats(self, owner: str) -> dict[str, int]:
        now = self._ctx.now()
        total, due, learned = self._repo.counts(owner, now)
        today = self._ctx.today(owner)
        days = [self._ctx.local_date(owner, t) for t in self._repo.review_times(owner)]
        return {
            "total": total,
            "due": due,
            "learned": learned,
            "streak_days": streak_days(set(days), today),
            "reviewed_today": sum(1 for d in days if d == today),
        }

    def topics(self, owner: str) -> Sequence[str]:
        return self._repo.topics(owner)


__all__ = ["LEARNED_BOX", "LearnService"]
