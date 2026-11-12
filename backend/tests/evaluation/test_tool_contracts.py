"""Every registered eval tool needs schema, access_kind, result_type, and a scenario."""

from __future__ import annotations

from tests.evaluation.harness import list_scenario_paths, load_scenario, registered_tool_specs


def _tools_referenced_by_scenarios() -> set[str]:
    names: set[str] = set()
    for path in list_scenario_paths():
        scenario = load_scenario(path)
        for turn in scenario.get("script") or []:
            for call in turn.get("tool_calls") or []:
                names.add(str(call["name"]))
        for name in (scenario.get("expect") or {}).get("tool_calls") or []:
            names.add(str(name))
        for name in (scenario.get("expect") or {}).get("forbidden_executed") or []:
            names.add(str(name))
    return names


def test_registered_tools_have_contracts(session_factory) -> None:
    specs = registered_tool_specs(session_factory)
    referenced = _tools_referenced_by_scenarios()
    missing_scenario: list[str] = []
    for spec in specs:
        assert spec.parameters_schema, f"{spec.name} missing schema"
        assert spec.access_kind in {"read", "prepare", "execute", "destructive"}, spec.name
        assert spec.result_type, f"{spec.name} missing result_type"
        if spec.name not in referenced:
            missing_scenario.append(spec.name)
    assert missing_scenario == [], f"tools without scenarios: {missing_scenario}"


def test_scenarios_do_not_define_spy_tools() -> None:
    for path in list_scenario_paths():
        scenario = load_scenario(path)
        assert not scenario.get("tools"), f"{path.name} still defines spy tools"
