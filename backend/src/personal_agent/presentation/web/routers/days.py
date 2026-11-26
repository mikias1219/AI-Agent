"""Days: summary, range, stats and carry-over (docs/LIFE_API_CONTRACT.md section 7).

Dates are read as plain strings and validated by the domain, so an invalid date is a 400 with
`{"detail": ...}` like the other life endpoints.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from personal_agent.app.container import AppContainer
from personal_agent.application.services.day_service import parse_day
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER

JsonBody = Annotated[dict[str, Any] | None, Body()]


def build_days_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["days"])
    owner = DASHBOARD_OWNER

    # Fixed paths come first: `/api/days/{date}` would otherwise swallow `range` and `stats`.
    @router.get("/api/days/range")
    def day_range(
        from_date: Annotated[str | None, Query(alias="from")] = None,
        to_date: Annotated[str | None, Query(alias="to")] = None,
    ) -> list[dict[str, Any]]:
        return container.days.range(owner, parse_day(from_date, "from"), parse_day(to_date, "to"))

    @router.get("/api/days/stats")
    def day_stats() -> dict[str, Any]:
        return container.days.stats(owner)

    @router.get("/api/review")
    def review(period: Annotated[str, Query()] = "week") -> dict[str, Any]:
        return container.review.build(owner, period)

    @router.get("/api/days/{day}")
    def get_day(day: str) -> dict[str, Any]:
        return container.days.day(owner, parse_day(day))

    @router.post("/api/days/{day}/carry-over")
    def carry_over(day: str, body: JsonBody = None) -> dict[str, Any]:
        target = (body or {}).get("to")
        return container.days.carry_over(
            owner, parse_day(day), parse_day(target, "to") if target else None
        )

    return router
