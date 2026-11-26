"""Payslip persistence (one row per owner and pay period)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.finance_periods import Payslip
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import FinPayslipRow

_FIELDS = (
    "owner_user_id",
    "period_start",
    "period_end",
    "payday",
    "components",
    "deductions",
    "gross_minor",
    "net_minor",
    "account_id",
    "transaction_id",
)


def _obj(r: FinPayslipRow) -> Payslip:
    return Payslip(
        r.id,
        r.owner_user_id,
        r.period_start,
        r.period_end,
        r.payday,
        dict(r.components or {}),
        dict(r.deductions or {}),
        r.gross_minor,
        r.net_minor,
        r.account_id,
        r.transaction_id,
    )


class PayslipRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def upsert(self, payslip: Payslip) -> Payslip:
        with session_scope(self._factory) as s:
            row = s.scalar(
                select(FinPayslipRow).where(
                    FinPayslipRow.owner_user_id == payslip.owner_user_id,
                    FinPayslipRow.period_start == payslip.period_start,
                )
            )
            if row is None:
                row = FinPayslipRow(id=payslip.id)
                s.add(row)
            else:
                payslip.id = row.id
            for name in _FIELDS:
                setattr(row, name, getattr(payslip, name))
            s.flush()
            return _obj(row)

    def list(self, owner: str, *, limit: int = 24) -> Sequence[Payslip]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinPayslipRow)
                .where(FinPayslipRow.owner_user_id == owner)
                .order_by(FinPayslipRow.period_start.desc())
                .limit(limit)
            )
            return [_obj(r) for r in rows]

    def latest(self, owner: str) -> Payslip | None:
        items = self.list(owner, limit=1)
        return items[0] if items else None

    def get(self, owner: str, payslip_id: str) -> Payslip | None:
        with session_scope(self._factory) as s:
            row = s.get(FinPayslipRow, payslip_id)
            return _obj(row) if row and row.owner_user_id == owner else None

    def delete(self, owner: str, payslip_id: str) -> bool:
        with session_scope(self._factory) as s:
            result = s.execute(
                delete(FinPayslipRow).where(
                    FinPayslipRow.id == payslip_id, FinPayslipRow.owner_user_id == owner
                )
            )
            return bool(result.rowcount)  # type: ignore[attr-defined]
