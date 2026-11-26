from datetime import date

import pytest

from personal_agent.domain import daily_score as ds
from personal_agent.domain import finance_periods as fp
from personal_agent.domain.life import LifeError

TODAY = date(2026, 11, 26)  # a Thursday


def test_ranges_for_every_switcher_value():
    assert fp.resolve_range("today", TODAY) == fp.DateRange(TODAY, TODAY)
    week = fp.resolve_range("week", TODAY)
    assert (week.first, week.last) == (date(2026, 11, 23), date(2026, 11, 29))
    assert fp.resolve_range("month", TODAY).first == date(2026, 11, 1)
    assert fp.resolve_range("last_month", TODAY).last == date(2026, 10, 31)
    assert fp.resolve_range("next_month", TODAY).first == date(2026, 12, 1)
    assert fp.resolve_range("year", TODAY).days == 365
    custom = fp.resolve_range("custom", TODAY, start=date(2026, 1, 1), end=date(2026, 1, 10))
    assert custom.days == 10


def test_pay_period_runs_payday_to_payday():
    rng = fp.resolve_range("month", TODAY, payday=10)
    assert (rng.first, rng.last) == (date(2026, 11, 10), date(2026, 12, 9))
    early = fp.resolve_range("month", date(2026, 11, 5), payday=10)
    assert (early.first, early.last) == (date(2026, 10, 10), date(2026, 11, 9))
    assert fp.resolve_range("last_month", TODAY, payday=10).first == date(2026, 10, 10)


@pytest.mark.parametrize(
    "kind,kwargs",
    [
        ("bogus", {}),
        ("custom", {}),
        ("custom", {"start": date(2026, 2, 1), "end": date(2026, 1, 1)}),
    ],
)
def test_bad_ranges_rejected(kind, kwargs):
    with pytest.raises(LifeError):
        fp.resolve_range(kind, TODAY, **kwargs)


def test_comparison_is_previous_equal_range():
    month = fp.resolve_range("month", TODAY)
    prev = fp.comparison_range("month", month)
    assert (prev.first, prev.last) == (date(2026, 10, 1), date(2026, 10, 31))
    week = fp.comparison_range("week", fp.resolve_range("week", TODAY))
    assert week.first == date(2026, 11, 16) and week.days == 7
    assert fp.comparison_range("today", fp.DateRange(TODAY, TODAY)).first == date(2026, 11, 25)
    year = fp.comparison_range("year", fp.resolve_range("year", TODAY))
    assert year.first == date(2025, 1, 1)


def test_change_pace_allowance():
    assert fp.change_pct(88, 100) == -12.0
    assert fp.change_pct(5, 0) is None
    assert fp.pace(500, 1000, 0.5) == 1.0
    assert fp.pace(600, 1000, 0.5) == 1.2
    assert fp.pace(1, 0, 0.5) is None
    assert fp.daily_allowance(9800, 10) == 980
    assert fp.daily_allowance(-5, 3) == 0
    month = fp.resolve_range("month", TODAY)
    assert fp.days_left_in(month, TODAY) == 5  # 26..30 inclusive
    assert fp.elapsed_share(month, date(2026, 12, 5)) == 1.0


def test_payslip_formulas_match_the_plan():
    comps = {
        "basic": 100_00,
        "allowance": 20_00,
        "benefit": 5_00,
        "incentive": 3_00,
        "performance": 2_00,
    }
    ded = {"income_tax": 20_00, "pension": 7_00, "loan": 3_00, "other": 1_00}
    gross = fp.gross_pay(comps)
    assert gross == 130_00
    assert fp.net_pay(gross, ded) == 99_00
    fp.validate_payslip(comps, ded)
    assert fp.pension_amount(100_00, 7) == 7_00
    assert fp.free_to_spend(99_00, 10_00, 30_00, 20_00) == 59_00
    assert fp.forecast_left(100, 30, 20, 10) == 40
    assert fp.variable_average([0, 300, 100]) == 200
    assert fp.variable_average([0, 0]) == 0


def test_payslip_validation():
    with pytest.raises(LifeError):
        fp.validate_payslip({"basic": 0}, {})
    with pytest.raises(LifeError):
        fp.validate_payslip({"basic": 10}, {"pension": 11})
    with pytest.raises(LifeError):
        fp.validate_payslip({"salary": 10}, {})
    with pytest.raises(LifeError):
        fp.validate_payslip({"basic": 10}, {"bribe": 1})


def test_default_split_never_loses_a_cent():
    split = fp.default_split(10_001)
    assert sum(split.values()) == 10_001
    assert split["needs"] == 5000 and split["wants"] == 3000


def test_score_renormalises_and_rest_day_is_neutral():
    areas = [
        ds.AreaScore("tasks", 30, 1.0, ""),
        ds.AreaScore("habits", 25, 0.5, ""),
        ds.AreaScore("learning", 15, None, ""),
    ]
    out = ds.compute(areas)
    assert out["total"] == round((30 + 12.5) / 55 * 100)
    assert ds.compute(areas, rest=True)["total"] is None
    assert ds.compute([ds.AreaScore("tasks", 30, None, "")])["total"] is None
    assert ds.ratio(0, 0) is None and ds.ratio(3, 2) == 1.0


def test_weights_must_total_100():
    assert ds.clean_weights(None)["tasks"] == 30
    assert ds.clean_weights({"tasks": 35, "habits": 20})["tasks"] == 35
    with pytest.raises(LifeError):
        ds.clean_weights({"tasks": 50})
    with pytest.raises(LifeError):
        ds.clean_weights({"mood": 10})
    assert ds.trend([None, 40, 80])["best_index"] == 2


# -- payroll rules ------------------------------------------------------------------------

from personal_agent.domain.finance_periods import (  # noqa: E402
    compute_deductions,
    income_tax,
    net_pay,
    period_range,
)


def test_income_tax_matches_selamnew_brackets():
    # birr -> tax in birr, values from the payroll tax table
    cases = {0: 0, 2_000: 0, 3_000: 150, 8_000: 1_150, 15_000: 3_200, 35_000: 10_200}
    for birr, tax in cases.items():
        assert income_tax(birr * 100) == tax * 100, birr


def test_compute_deductions_fills_tax_and_pension_and_keeps_overrides():
    comps = {"basic": 3_500_000}
    auto = compute_deductions(comps, {})
    assert auto == {"income_tax": 1_020_000, "pension": 245_000}
    assert net_pay(3_500_000, auto) == 2_235_000  # 22,350 ETB
    typed = compute_deductions(comps, {"income_tax": 1_000_000, "loan": 50_000})
    assert typed["income_tax"] == 1_000_000 and typed["pension"] == 245_000
    assert typed["loan"] == 50_000


def test_pay_period_runs_tenth_to_ninth():
    from datetime import date

    rng = period_range(10, date(2026, 11, 26))
    assert (rng.first, rng.last) == (date(2026, 11, 10), date(2026, 12, 9))
    early = period_range(10, date(2026, 11, 3))
    assert (early.first, early.last) == (date(2026, 10, 10), date(2026, 11, 9))
