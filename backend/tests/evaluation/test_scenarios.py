"""Parametrized OBS-03 evaluation scenarios (scripted provider, offline)."""

from __future__ import annotations

import pytest

from tests.evaluation.harness import list_scenario_paths, load_scenario, run_scenario

SCENARIO_PATHS = list_scenario_paths()


@pytest.mark.parametrize("path", SCENARIO_PATHS, ids=[p.stem for p in SCENARIO_PATHS])
def test_eval_scenario(path, session_factory):
    scenario = load_scenario(path)
    result = run_scenario(scenario, session_factory)
    assert result.passed, "; ".join(result.errors)
