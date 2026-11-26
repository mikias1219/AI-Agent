"""Daily score (Improvement Plan: day-to-day improvement tracker).

One 0-100 number from five areas. An area with nothing planned/due is left out and the other
weights are re-normalised, so a day with no habits is not punished. A rest or sick day is
neutral: no score, no streak damage.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from personal_agent.domain.life import LifeError

AREAS = ("tasks", "habits", "learning", "money", "reflection")
DEFAULT_WEIGHTS: Mapping[str, int] = {
    "tasks": 30,
    "habits": 25,
    "learning": 15,
    "money": 15,
    "reflection": 15,
}
REST_STATUSES = ("rest", "sick")
P23_BONUS_CAP = 0.2


def clean_weights(raw: Mapping[str, Any] | None) -> dict[str, int]:
    """Validate editable weights: known areas, whole numbers, total 100."""
    if not raw:
        return dict(DEFAULT_WEIGHTS)
    weights = dict(DEFAULT_WEIGHTS)
    for name, value in raw.items():
        if name not in AREAS:
            raise LifeError(f"Unknown score area: {name}.")
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise LifeError(f"{name} weight must be a whole number from 0 to 100.")
        weights[name] = value
    if sum(weights.values()) != 100:
        raise LifeError("Score weights must add up to 100.")
    return weights


def ratio(done: float, planned: float, bonus: float = 0.0) -> float | None:
    """done / planned in 0..1; None when nothing was planned. `bonus` is capped."""
    if planned <= 0:
        return None
    return min(1.0, done / planned + min(max(bonus, 0.0), P23_BONUS_CAP))


@dataclass(frozen=True, slots=True)
class AreaScore:
    area: str
    weight: int
    ratio: float | None  # None = not measured today
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "weight": self.weight,
            "ratio": None if self.ratio is None else round(self.ratio, 3),
            "points": None if self.ratio is None else round(self.ratio * self.weight, 1),
            "detail": self.detail,
        }


def compute(areas: list[AreaScore], *, rest: bool = False) -> dict[str, Any]:
    """Total 0-100 (None on a rest day or when no area was measured) plus the breakdown."""
    measured = [a for a in areas if a.ratio is not None and a.weight > 0]
    total: int | None
    if rest or not measured:
        total = None
    else:
        weight_sum = sum(a.weight for a in measured)
        total = round(
            sum(a.ratio * a.weight for a in measured if a.ratio is not None) / weight_sum * 100
        )
    return {
        "total": total,
        "rest": rest,
        "areas": [a.to_dict() for a in areas],
        "label": label(total, rest),
    }


def label(total: int | None, rest: bool = False) -> str:
    if rest:
        return "Rest day"
    if total is None:
        return "Nothing to score yet"
    if total >= 80:
        return "Strong day"
    if total >= 50:
        return "On track"
    return "Slow day"


def trend(scores: list[int | None]) -> dict[str, Any]:
    """Weekly view: average, best and worst day over the scored days."""
    scored = [(i, s) for i, s in enumerate(scores) if s is not None]
    if not scored:
        return {"average": None, "best_index": None, "worst_index": None}
    return {
        "average": round(sum(s for _, s in scored) / len(scored)),
        "best_index": max(scored, key=lambda p: p[1])[0],
        "worst_index": min(scored, key=lambda p: p[1])[0],
    }
