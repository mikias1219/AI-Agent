"""Reading plans, templates, logs and stats (contract section 4). References only."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.life import (
    LifeConflict,
    LifeError,
    ReadingLog,
    ReadingPlan,
    clean_reading_items,
    clean_reading_log,
    clean_reading_name,
    page_args,
    reading_templates,
    same_reference,
    streak_days,
)
from personal_agent.domain.ports import ReadingRepository

PLAN_FINISHED = "This plan is finished."


class ReadingService:
    def __init__(self, repository: ReadingRepository, ctx: LifeContext) -> None:
        self._repo = repository
        self._ctx = ctx

    # -- plans ----------------------------------------------------------------------

    def templates(self) -> list[dict[str, Any]]:
        return [
            {"id": t.id, "name": t.name, "description": t.description, "count": len(t.items)}
            for t in reading_templates().values()
        ]

    def create_plan(self, owner: str, data: Mapping[str, Any]) -> ReadingPlan:
        name = clean_reading_name(data)
        items: list[str]
        if data.get("items") is not None:
            items = clean_reading_items(data["items"])
        elif data.get("template") is not None:
            template = reading_templates().get(str(data["template"]))
            if template is None:
                raise LifeError("Unknown template.")
            items = list(template.items)
        else:
            items = []
        now = self._ctx.now()
        plan = ReadingPlan(
            id=uuid.uuid4().hex,
            owner_user_id=owner,
            name=name,
            items=items,
            position=0,
            active=True,
            created_at=now,
            updated_at=now,
        )
        self._repo.add_plan(plan)
        self._ctx.record("reading.plan_created", owner, id=plan.id, items=len(items))
        return plan

    def get_plan(self, owner: str, plan_id: str) -> ReadingPlan:
        plan = self._repo.get_plan(owner, plan_id)
        if plan is None:
            raise not_found("Reading plan")
        return plan

    def update_plan(self, owner: str, plan_id: str, data: Mapping[str, Any]) -> ReadingPlan:
        plan = self.get_plan(owner, plan_id)
        if "name" in data:
            plan.name = clean_reading_name(data)
        if "active" in data:
            if not isinstance(data["active"], bool):
                raise LifeError("active must be true or false.")
            plan.active = data["active"]
        if "position" in data:
            position = data["position"]
            if isinstance(position, bool) or not isinstance(position, int):
                raise LifeError("position must be an integer.")
            if not 0 <= position <= len(plan.items):
                raise LifeError(f"position must be between 0 and {len(plan.items)}.")
            plan.position = position
        plan.updated_at = self._ctx.now()
        self._repo.save_plan(plan)
        self._ctx.record("reading.plan_updated", owner, id=plan.id)
        return plan

    def delete_plan(self, owner: str, plan_id: str) -> None:
        if not self._repo.delete_plan(owner, plan_id):
            raise not_found("Reading plan")
        self._ctx.record("reading.plan_deleted", owner, id=plan_id)

    def list_plans(
        self, owner: str, *, limit: int | None = None, offset: int | None = None
    ) -> Sequence[ReadingPlan]:
        lim, off = page_args(limit, offset)
        return self._repo.list_plans(owner, limit=lim, offset=off)

    def active_plan(self, owner: str) -> ReadingPlan | None:
        """Newest active plan that still has something left to read."""
        for plan in self._repo.list_plans(owner, limit=200, offset=0):
            if plan.active and plan.next is not None:
                return plan
        return None

    def advance(
        self, owner: str, plan_id: str, reflection: str = ""
    ) -> tuple[ReadingPlan, ReadingLog]:
        plan = self.get_plan(owner, plan_id)
        reference = plan.next
        if reference is None:
            raise LifeConflict(PLAN_FINISHED)
        fields = clean_reading_log({"reference": reference, "reflection": reflection})
        log = self._new_log(owner, fields["reference"], self._ctx.today(owner), fields, plan.id)
        self._repo.add_log(log)
        plan.position += 1
        plan.updated_at = self._ctx.now()
        self._repo.save_plan(plan)
        self._ctx.record("reading.advanced", owner, plan_id=plan.id, log_id=log.id)
        return plan, log

    # -- logs -----------------------------------------------------------------------

    def _new_log(
        self,
        owner: str,
        reference: str,
        read_on: Any,
        fields: Mapping[str, Any],
        plan_id: str | None,
    ) -> ReadingLog:
        return ReadingLog(
            id=uuid.uuid4().hex,
            owner_user_id=owner,
            reference=reference,
            read_on=fields.get("read_on", read_on),
            reflection=fields.get("reflection", ""),
            plan_id=plan_id,
            created_at=self._ctx.now(),
        )

    def create_log(self, owner: str, data: Mapping[str, Any]) -> ReadingLog:
        fields = clean_reading_log(data)
        plan_id = data.get("plan_id")
        if plan_id is not None:
            if not isinstance(plan_id, str):
                raise LifeError("plan_id must be a string.")
            self.get_plan(owner, plan_id)
        log = self._new_log(owner, fields["reference"], self._ctx.today(owner), fields, plan_id)
        self._repo.add_log(log)
        self._ctx.record("reading.logged", owner, id=log.id)
        return log

    def log_reference(
        self, owner: str, reference: str, reflection: str = ""
    ) -> tuple[ReadingLog, ReadingPlan | None]:
        """Agent path: log a reading; advance the active plan when it matches `next`."""
        plan = self.active_plan(owner)
        if plan is not None and plan.next is not None and same_reference(plan.next, reference):
            advanced, log = self.advance(owner, plan.id, reflection)
            return log, advanced
        fields = clean_reading_log({"reference": reference, "reflection": reflection})
        log = self._new_log(owner, fields["reference"], self._ctx.today(owner), fields, None)
        self._repo.add_log(log)
        self._ctx.record("reading.logged", owner, id=log.id, source="agent")
        return log, None

    def get_log(self, owner: str, log_id: str) -> ReadingLog:
        log = self._repo.get_log(owner, log_id)
        if log is None:
            raise not_found("Reading log")
        return log

    def update_log(self, owner: str, log_id: str, data: Mapping[str, Any]) -> ReadingLog:
        log = self.get_log(owner, log_id)
        for key, value in clean_reading_log(data, partial=True).items():
            setattr(log, key, value)
        self._repo.save_log(log)
        self._ctx.record("reading.log_updated", owner, id=log.id)
        return log

    def delete_log(self, owner: str, log_id: str) -> None:
        if not self._repo.delete_log(owner, log_id):
            raise not_found("Reading log")
        self._ctx.record("reading.log_deleted", owner, id=log_id)

    def list_logs(
        self,
        owner: str,
        *,
        plan_id: str = "",
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[ReadingLog]:
        lim, off = page_args(limit, offset)
        return self._repo.list_logs(owner, plan_id=plan_id, limit=lim, offset=off)

    def stats(self, owner: str) -> dict[str, Any]:
        today = self._ctx.today(owner)
        days = set(self._repo.log_dates(owner))
        return {
            "logs": self._repo.log_count(owner),
            "streak_days": streak_days(days, today),
            "read_today": today in days,
            "active_plan": self.active_plan(owner),
        }
