# ADR 0037: Money by period, payslips and the day score

Status: accepted. Source: Compass_AURA_Improvement_Plan.docx.

## Decision

- **Period engine** (`domain/finance_periods.py`): one switcher value (today, week, month, last
  month, next month, year, custom) resolves to a date range. Every total is compared with the
  previous equal range. When a payslip exists, "month" views follow the payday-to-payday period.
  Transfers are never income or expense; Savings and Emergency categories count as saved.
- **Payslips** (`fin_payslips`, one row per owner and pay period): income components and
  deductions stored as JSON in minor units; gross and net are computed in the domain, never
  trusted from the client. Saving the same period again updates it and logs income only once.
- **Forecast** for a range that has not started: last payslip net plus scheduled income, minus
  bills due, the 3-month average of non-fixed spend and planned savings. It is labelled as a
  forecast and warns under a safety buffer (default 2,000 ETB).
- **Day score** (`domain/daily_score.py`): tasks 30, habits 25, learning 15, money 15,
  reflection 15. Areas with nothing to measure are dropped and the rest re-normalised; a rest
  day has no score. Reflection only counts against the owner after 20:00.
- Task titles are checked by `title_issue` and surfaced; nothing is deleted automatically.
- Added composite index `(owner_user_id, occurred_at)` on `fin_transactions`.
  Migration `20261201_01` works on SQLite and Postgres.

## Not done yet (from the plan)

Unusual-spend flag, accounts-reconcile flow, receipt and SMS capture, month close, autonomy
levels per action, Today evening mode and timeline, React Bits components, Ctrl K actions,
spaced-repetition schedule changes, data export. Tax brackets and score weights are defaults;
Settings screens for them are not built.
