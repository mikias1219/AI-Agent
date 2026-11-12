"""SQLAlchemy-backed goal and plan repositories (SQLite and Postgres)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.goals import Goal, Plan, PlanStep
from personal_agent.domain.ports import GoalRepository, PlanRepository
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import GoalRow, PlanRow, PlanStepRow


def _goal(row: GoalRow) -> Goal:
    return Goal(
        id=row.id,
        owner_user_id=row.owner_user_id,
        title=row.title,
        success_criteria=list(row.success_criteria or []),
        progress=float(row.progress or 0.0),
        status=row.status,
        next_step=row.next_step or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class GoalRepositoryImpl(GoalRepository):
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, goal: Goal) -> None:
        with session_scope(self._factory) as session:
            session.add(
                GoalRow(
                    id=goal.id,
                    owner_user_id=goal.owner_user_id,
                    title=goal.title,
                    success_criteria=list(goal.success_criteria),
                    progress=goal.progress,
                    status=goal.status,
                    next_step=goal.next_step,
                    **_stamps(goal.created_at, goal.updated_at),
                )
            )

    def get(self, goal_id: str) -> Goal | None:
        with session_scope(self._factory) as session:
            row = session.get(GoalRow, goal_id)
            return _goal(row) if row else None

    def save(self, goal: Goal) -> None:
        with session_scope(self._factory) as session:
            row = session.get(GoalRow, goal.id)
            if row is None:
                raise StorageError(f"Unknown goal '{goal.id}'.")
            row.title = goal.title
            row.success_criteria = list(goal.success_criteria)
            row.progress = goal.progress
            row.status = goal.status
            row.next_step = goal.next_step
            if goal.updated_at is not None:
                row.updated_at = goal.updated_at

    def list(self, owner_user_id: str, status: str | None = None) -> list[Goal]:
        with session_scope(self._factory) as session:
            query = session.query(GoalRow).filter(GoalRow.owner_user_id == owner_user_id)
            if status is not None:
                query = query.filter(GoalRow.status == status)
            rows = query.order_by(GoalRow.created_at.desc(), GoalRow.id.desc()).all()
            return [_goal(r) for r in rows]


def _stamps(created_at: datetime | None, updated_at: datetime | None) -> dict[str, datetime]:
    stamps: dict[str, datetime] = {}
    if created_at is not None:
        stamps["created_at"] = created_at
    if updated_at is not None:
        stamps["updated_at"] = updated_at
    return stamps


def _step_row(plan_id: str, position: int, step: PlanStep) -> PlanStepRow:
    return PlanStepRow(
        id=step.id,
        plan_id=plan_id,
        position=position,
        title=step.title,
        tool_name=step.tool_name,
        access_kind=step.access_kind,
        status=step.status,
        depends_on=list(step.depends_on),
    )


def _plan(row: PlanRow, step_rows: list[PlanStepRow]) -> Plan:
    return Plan(
        id=row.id,
        goal_id=row.goal_id,
        owner_user_id=row.owner_user_id,
        title=row.title or "",
        status=row.status,
        steps=[
            PlanStep(
                id=s.id,
                title=s.title,
                tool_name=s.tool_name,
                access_kind=s.access_kind,
                status=s.status,
                depends_on=list(s.depends_on or []),
            )
            for s in sorted(step_rows, key=lambda r: r.position)
        ],
        created_at=row.created_at,
        updated_at=row.updated_at,
        approved_at=row.approved_at,
    )


class PlanRepositoryImpl(PlanRepository):
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def add(self, plan: Plan) -> None:
        with session_scope(self._factory) as session:
            session.add(
                PlanRow(
                    id=plan.id,
                    goal_id=plan.goal_id,
                    owner_user_id=plan.owner_user_id,
                    title=plan.title,
                    status=plan.status,
                    approved_at=plan.approved_at,
                    **_stamps(plan.created_at, plan.updated_at),
                )
            )
            session.flush()  # parent row first so the FK holds on Postgres
            for position, step in enumerate(plan.steps):
                session.add(_step_row(plan.id, position, step))

    def _steps(self, session: Session, plan_id: str) -> list[PlanStepRow]:
        return session.query(PlanStepRow).filter(PlanStepRow.plan_id == plan_id).all()

    def get(self, plan_id: str) -> Plan | None:
        with session_scope(self._factory) as session:
            row = session.get(PlanRow, plan_id)
            return _plan(row, self._steps(session, plan_id)) if row else None

    def save(self, plan: Plan) -> None:
        with session_scope(self._factory) as session:
            row = session.get(PlanRow, plan.id)
            if row is None:
                raise StorageError(f"Unknown plan '{plan.id}'.")
            row.goal_id = plan.goal_id
            row.title = plan.title
            row.status = plan.status
            row.approved_at = plan.approved_at
            if plan.updated_at is not None:
                row.updated_at = plan.updated_at
            existing = {s.id: s for s in self._steps(session, plan.id)}
            keep = {s.id for s in plan.steps}
            for step_id, step_row in existing.items():
                if step_id not in keep:
                    session.delete(step_row)
            for position, step in enumerate(plan.steps):
                step_row = existing.get(step.id)
                if step_row is None:
                    session.add(_step_row(plan.id, position, step))
                    continue
                step_row.position = position
                step_row.title = step.title
                step_row.tool_name = step.tool_name
                step_row.access_kind = step.access_kind
                step_row.status = step.status
                step_row.depends_on = list(step.depends_on)

    def list(self, owner_user_id: str, goal_id: str | None = None) -> list[Plan]:
        with session_scope(self._factory) as session:
            query = session.query(PlanRow).filter(PlanRow.owner_user_id == owner_user_id)
            if goal_id is not None:
                query = query.filter(PlanRow.goal_id == goal_id)
            rows = query.order_by(PlanRow.created_at.desc(), PlanRow.id.desc()).all()
            return [_plan(r, self._steps(session, r.id)) for r in rows]
