"""Daily wrap-up routine (contract section 10, BR-14): suggestion, carry-over and sync requests."""

from __future__ import annotations

from datetime import date

import pytest

from tests.sync_support import ALL_SCOPES, OWNER, Clock, build_sync_app, dashboard_client, utc

EVENING = utc(2026, 11, 25, 21, 5)


@pytest.fixture()
def env(tmp_path):
    clock = Clock(EVENING)
    container, fake = build_sync_app(tmp_path, clock)
    return container, fake, clock


def automation(container):
    container.automations.ensure_defaults(OWNER)
    return next(a for a in container.automations.list(OWNER) if a.kind == "daily_wrapup")


def enable(container):
    row = automation(container)
    row.enabled = True
    container.automations.save(row)
    return row


def add_tasks(container, done=0, partial=0, missed=0, skipped=0, open_=0, due=None):
    for index in range(done + partial + missed + skipped + open_):
        container.tasks.create(f"Task {index}", owner_user_id=OWNER, due_at=due, timezone="UTC")
    tasks = container.tasks.tasks_on(OWNER, container.days.today(OWNER))
    cursor = 0
    for count, outcome in (
        (done, "achieved"),
        (partial, "partial"),
        (missed, "missed"),
        (skipped, "skipped"),
    ):
        for _ in range(count):
            container.tasks.complete(tasks[cursor].id, outcome=outcome)
            cursor += 1
    return tasks


def run_now(container):
    row = enable(container)
    result = container.scheduler.run_automation_now(row.id, OWNER)
    return result["automation"].last_result


def open_suggestions(container):
    return list(container.suggestions.open(OWNER))


def test_catalogue_entry_defaults_to_off_at_21(env) -> None:
    container, _, _ = env
    from personal_agent.application.services.routine_catalog import catalogue_by_kind

    spec = catalogue_by_kind()["daily_wrapup"]
    assert (spec.schedule_time, spec.enabled_by_default) == ("21:00", False)
    row = automation(container)
    assert row.enabled is False and row.schedule_time == "21:00"


def test_suggestion_summarises_the_day_and_offers_the_carry_over(env) -> None:
    container, _, _ = env
    add_tasks(container, done=4, open_=1)
    run_now(container)
    [suggestion] = open_suggestions(container)
    assert suggestion.title == (
        "Today: 4 of 5 done (80%). Carry 1 unfinished task over to tomorrow?"
    )
    assert suggestion.source == "routine:daily_wrapup"
    assert suggestion.proposed_action == {
        "tool_name": "day_carry_over",
        "arguments": {"date": "2026-11-25", "to": "2026-11-26"},
    }


def test_title_pluralises_and_counts_partial_credit(env) -> None:
    container, _, _ = env
    add_tasks(container, done=1, partial=1, missed=1, open_=2)
    run_now(container)
    [suggestion] = open_suggestions(container)
    assert suggestion.title == (
        "Today: 2 of 5 done (30%). Carry 2 unfinished tasks over to tomorrow?"
    )


def test_accepting_performs_the_carry_over_through_the_registry(env) -> None:
    container, _, _ = env
    tasks = add_tasks(container, done=2, open_=2)
    run_now(container)
    [suggestion] = open_suggestions(container)
    result = container.suggestions.accept(suggestion.id, OWNER)
    assert result.outcome == "done" and "Moved 2" in result.summary
    moved = [t for t in container.tasks.tasks_on(OWNER, date(2026, 11, 26))]
    assert len(moved) == 2 and all(t.status.value == "planned" for t in moved)
    done = [t for t in container.tasks.tasks_on(OWNER, container.days.today(OWNER))]
    assert len(done) == 2 and {t.id for t in done}.isdisjoint({t.id for t in moved})
    assert len(tasks) == 4


def test_finished_day_has_no_carry_over(env) -> None:
    container, _, _ = env
    add_tasks(container, done=3)
    run_now(container)
    [suggestion] = open_suggestions(container)
    assert suggestion.title == "Today: 3 of 3 done (100%)."
    assert suggestion.proposed_action == {}


def test_nothing_is_created_when_there_were_no_tasks(env) -> None:
    container, _, _ = env
    summary = run_now(container)
    assert "No tasks today" in summary
    assert open_suggestions(container) == []
    assert container.approvals_repository.find(limit=5) == []


def test_quiet_hours_pause_and_cap_are_respected(env) -> None:
    container, fake, _ = env
    add_tasks(container, done=1, open_=1)
    container.drive_sync.update_settings(OWNER, enabled=True)
    container.notifications.update(
        OWNER, {"quiet_hours": {"enabled": True, "start": "21:00", "end": "07:00"}}
    )
    summary = run_now(container)
    assert "skipped" in summary.lower()
    assert open_suggestions(container) == [] and container.approvals_repository.find(limit=5) == []
    assert fake.requests == []

    container.notifications.update(OWNER, {"quiet_hours": {"enabled": False}})
    container.agent_control.patch(OWNER, paused=True)
    assert "skipped" in run_now(container).lower()
    assert open_suggestions(container) == []
    container.agent_control.patch(OWNER, paused=False)

    for _ in range(3):  # default daily proactive cap is 3
        container.agent_control.record_proactive(OWNER)
    assert "skipped" in run_now(container).lower()
    assert open_suggestions(container) == []


def test_automation_quiet_hours_apply_too(env) -> None:
    container, _, _ = env
    add_tasks(container, done=1)
    row = enable(container)
    row.quiet_hours_start, row.quiet_hours_end = "20:00", "23:00"
    container.automations.save(row)
    result = container.scheduler.run_automation_now(row.id, OWNER)
    assert "skipped" in result["automation"].last_result.lower()
    assert open_suggestions(container) == []


def test_drive_and_calendar_batches_are_requested_through_the_registry_in_ask_mode(env) -> None:
    container, fake, _ = env
    container.notes.create(OWNER, {"kind": "note", "title": "Idea", "body": "x"})
    add_tasks(container, done=1, due=utc(2026, 11, 25, 22, 30))
    container.drive_sync.update_settings(OWNER, enabled=True)
    container.calendar_sync.update_settings(OWNER, enabled=True)
    summary = run_now(container)
    assert "Drive: awaiting_approval" in summary and "Calendar: awaiting_approval" in summary
    approvals = container.approvals_repository.find(limit=10)
    assert sorted(a.tool_name for a in approvals) == ["drive_sync_push", "task_calendar_sync"]
    drive = next(a for a in approvals if a.tool_name == "drive_sync_push")
    kinds = {i["type"] for i in drive.arguments["items"]}
    assert {"note", "daily"} <= kinds
    assert all(a.origin == "automation" for a in approvals)
    assert fake.requests == []  # nothing written without the owner's approval


def test_auto_mode_runs_both_batches(env) -> None:
    container, fake, _ = env
    container.notes.create(OWNER, {"kind": "note", "title": "Idea", "body": "x"})
    add_tasks(container, done=1, due=utc(2026, 11, 25, 22, 30))
    container.drive_sync.update_settings(OWNER, enabled=True)
    container.calendar_sync.update_settings(OWNER, enabled=True)
    container.agent_control.patch(
        OWNER, tool_permissions={"drive_sync_push": "allow", "task_calendar_sync": "allow"}
    )
    summary = run_now(container)
    assert "Drive: done" in summary and "Calendar: done" in summary
    assert container.approvals_repository.find(limit=5) == []
    assert len(fake.uploads()) >= 2 and len(fake.events) == 1


def test_sync_is_only_requested_when_enabled(env) -> None:
    container, fake, _ = env
    add_tasks(container, done=1)
    summary = run_now(container)
    assert "Drive" not in summary and "Calendar" not in summary
    assert fake.requests == [] and container.approvals_repository.find(limit=5) == []


def test_enabled_sync_that_cannot_run_is_reported_not_raised(tmp_path) -> None:
    container, fake = build_sync_app(tmp_path, Clock(EVENING), scopes=None)
    add_tasks(container, done=1)
    container.drive_sync.update_settings(OWNER, enabled=True)
    summary = run_now(container)
    assert "Drive: skipped (Google Drive is not connected.)" in summary
    assert len(open_suggestions(container)) == 1  # the suggestion still happens
    assert fake.requests == []


def test_scheduler_runs_it_once_at_the_chosen_time(env) -> None:
    container, _, clock = env
    add_tasks(container, done=1, open_=1)
    row = enable(container)
    row.schedule_time = "21:30"
    container.automations.save(row)
    container.scheduler.tick()
    assert open_suggestions(container) == []  # 21:05 is before 21:30
    clock.advance(minutes=30)
    container.scheduler.tick()
    assert len(open_suggestions(container)) == 1
    container.scheduler.tick()
    assert len(open_suggestions(container)) == 1  # once per day


def test_notification_prefs_enforce_wrapup_flag_and_time(tmp_path, monkeypatch) -> None:
    container, _ = build_sync_app(tmp_path, Clock(EVENING), scopes=ALL_SCOPES)
    client = dashboard_client(container, tmp_path, monkeypatch)
    prefs = client.get("/api/profile/notifications").json()
    assert prefs["daily_wrapup"] is False and prefs["wrapup_time"] == "21:00"
    assert {"daily_wrapup", "wrapup_time"} <= set(prefs["enforced"])
    patched = client.patch(
        "/api/profile/notifications", json={"daily_wrapup": True, "wrapup_time": "20:15"}
    ).json()
    assert patched["daily_wrapup"] is True and patched["wrapup_time"] == "20:15"
    row = automation(container)
    assert row.enabled is True and row.schedule_time == "20:15"
    assert (
        client.patch("/api/profile/notifications", json={"wrapup_time": "25:00"}).status_code == 400
    )
    assert (
        client.patch("/api/profile/notifications", json={"daily_wrapup": "yes"}).status_code == 400
    )
