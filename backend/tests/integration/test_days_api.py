"""Tasks as achievements and days (contract section 7): API, tools, Today, export and wipe."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from personal_agent.domain.models import ToolCall, ToolContext
from tests.sync_support import OWNER, Clock, build_sync_app, dashboard_client, utc

NOW = utc(2026, 11, 25, 12)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    clock = Clock(NOW)
    container, fake = build_sync_app(tmp_path, clock, scopes=None)
    return container, dashboard_client(container, tmp_path, monkeypatch), clock


def make(client, title="Push-ups", **extra):
    resp = client.post("/api/tasks", json={"title": title, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def call(container, name, **arguments):
    ctx = ToolContext(user_id=OWNER, session_id="s1", origin="cli")
    result = container.registry.execute(ToolCall(id="c1", name=name, arguments=arguments), ctx)
    return result, (json.loads(result.output) if result.ok else {})


# -- task fields -------------------------------------------------------------------------------


def test_new_task_fields_and_defaults(env) -> None:
    _, client, _ = env
    task = make(client)
    assert task["plan_date"] == "2026-11-25"
    assert (task["target_value"], task["target_unit"], task["actual_value"]) == (None, "", None)
    assert (task["outcome"], task["outcome_note"]) == (None, "")
    assert (task["calendar_event_id"], task["calendar_synced_at"]) == (None, None)


def test_plan_date_follows_due_date_unless_given(env) -> None:
    _, client, _ = env
    assert make(client, due="2026-12-01 15:00")["plan_date"] == "2026-12-01"
    assert make(client, due="2026-12-01 15:00", plan_date="2026-12-03")["plan_date"] == "2026-12-03"


def test_target_and_validation(env) -> None:
    _, client, _ = env
    task = make(client, target_value=30, target_unit="push-ups")
    assert (task["target_value"], task["target_unit"]) == (30.0, "push-ups")
    assert (
        client.post("/api/tasks", json={"title": "x", "target_unit": "u" * 21}).status_code == 422
    )
    assert client.post("/api/tasks", json={"title": "x", "actual_value": -1}).status_code == 422
    assert client.post("/api/tasks", json={"title": "x", "outcome": "great"}).status_code == 422


def test_patch_accepts_new_fields_and_clears_target(env) -> None:
    _, client, _ = env
    task = make(client, target_value=30, target_unit="reps")
    patched = client.patch(
        f"/api/tasks/{task['id']}",
        json={"plan_date": "2026-11-28", "target_unit": "push-ups", "outcome_note": "hard"},
    ).json()
    assert (patched["plan_date"], patched["target_unit"], patched["outcome_note"]) == (
        "2026-11-28",
        "push-ups",
        "hard",
    )
    assert patched["target_value"] == 30.0
    cleared = client.patch(f"/api/tasks/{task['id']}", json={"target_value": None}).json()
    assert cleared["target_value"] is None


def test_patch_outcome_closes_the_task(env) -> None:
    _, client, _ = env
    task = make(client, target_value=30)
    done = client.patch(
        f"/api/tasks/{task['id']}", json={"outcome": "partial", "actual_value": 10}
    ).json()
    assert (done["status"], done["outcome"], done["actual_value"]) == ("done", "partial", 10.0)
    assert done["completed_at"] is not None


# -- complete and reopen -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("outcome", "status", "completed"),
    [
        ("achieved", "done", True),
        ("partial", "done", True),
        ("missed", "cancelled", False),
        ("skipped", "cancelled", False),
    ],
)
def test_complete_with_each_outcome(env, outcome, status, completed) -> None:
    _, client, _ = env
    task = make(client)
    resp = client.post(f"/api/tasks/{task['id']}/complete", json={"outcome": outcome, "note": "n"})
    assert resp.status_code == 200
    body = resp.json()
    assert (body["status"], body["outcome"], body["outcome_note"]) == (status, outcome, "n")
    assert (body["completed_at"] is not None) is completed


def test_complete_infers_outcome_from_target(env) -> None:
    _, client, _ = env
    cases = [
        (30, "achieved", "done"),
        (45, "achieved", "done"),
        (12, "partial", "done"),
        (0, "missed", "cancelled"),
    ]
    for actual, outcome, status in cases:
        task = make(client, target_value=30, target_unit="push-ups")
        body = client.post(
            f"/api/tasks/{task['id']}/complete", json={"actual_value": actual}
        ).json()
        assert (body["outcome"], body["status"], body["actual_value"]) == (outcome, status, actual)


def test_complete_without_body_target_or_actual_is_achieved(env) -> None:
    _, client, _ = env
    assert client.post(f"/api/tasks/{make(client)['id']}/complete").json()["outcome"] == "achieved"
    with_target = make(client, target_value=5)
    assert (
        client.post(f"/api/tasks/{with_target['id']}/complete", json={}).json()["outcome"]
        == "achieved"
    )


def test_complete_errors(env) -> None:
    _, client, _ = env
    assert client.post("/api/tasks/missing/complete", json={}).status_code == 404
    task = make(client)
    assert (
        client.post(f"/api/tasks/{task['id']}/complete", json={"actual_value": -2}).status_code
        == 422
    )
    assert (
        client.post(f"/api/tasks/{task['id']}/complete", json={"outcome": "x"}).status_code == 422
    )


def test_reopen_clears_outcome_actual_and_completion(env) -> None:
    _, client, _ = env
    for outcome in ("achieved", "missed"):
        task = make(client, target_value=30)
        client.post(
            f"/api/tasks/{task['id']}/complete", json={"outcome": outcome, "actual_value": 3}
        )
        reopened = client.post(f"/api/tasks/{task['id']}/reopen").json()
        assert reopened["status"] == "planned"
        assert (reopened["outcome"], reopened["actual_value"], reopened["completed_at"]) == (
            None,
            None,
            None,
        )


def test_existing_status_patch_still_works(env) -> None:
    _, client, _ = env
    task = make(client)
    done = client.patch(f"/api/tasks/{task['id']}", json={"status": "done"}).json()
    assert done["status"] == "done" and done["completed_at"] and done["outcome"] == "achieved"
    assert (
        client.patch(f"/api/tasks/{task['id']}", json={"status": "planned"}).json()["outcome"]
        is None
    )


# -- filters -----------------------------------------------------------------------------------


def test_plan_date_and_range_filters(env) -> None:
    _, client, _ = env
    a = make(client, "A", plan_date="2026-11-20")
    b = make(client, "B", plan_date="2026-11-22")
    c = make(client, "C", plan_date="2026-11-25")
    ids = lambda params: {t["id"] for t in client.get("/api/tasks", params=params).json()}  # noqa: E731
    assert ids({"plan_date": "2026-11-22"}) == {b["id"]}
    assert ids({"from": "2026-11-21", "to": "2026-11-25"}) == {b["id"], c["id"]}
    assert ids({"from": "2026-11-22"}) == {b["id"], c["id"]}
    assert ids({"to": "2026-11-20"}) == {a["id"]}
    assert ids({"status": "planned", "plan_date": "2026-11-25"}) == {c["id"]}


# -- days --------------------------------------------------------------------------------------


def seed_day(client, plan_date, outcomes, open_count=0):
    for index, outcome in enumerate(outcomes):
        task = make(client, f"{plan_date}-{index}", plan_date=plan_date)
        client.post(f"/api/tasks/{task['id']}/complete", json={"outcome": outcome})
    for index in range(open_count):
        make(client, f"{plan_date}-open-{index}", plan_date=plan_date)


def test_day_payload_shape_and_summary(env) -> None:
    container, client, _ = env
    seed_day(client, "2026-11-25", ["achieved", "achieved", "partial", "missed", "skipped"], 1)
    container.notes.create(OWNER, {"kind": "diary", "body": "a day", "entry_date": "2026-11-25"})
    container.reading.create_log(OWNER, {"reference": "John 1"})
    created, _ = container.learn.create_many(OWNER, [{"term": "habari", "meaning": "news"}])
    container.learn.review(OWNER, created[0].id, "know")
    day = client.get("/api/days/2026-11-25").json()
    assert set(day) == {
        "date",
        "is_today",
        "tasks",
        "summary",
        "events",
        "calendar_connected",
        "diary",
        "readings",
        "learned",
    }
    assert day["is_today"] is True and day["calendar_connected"] is False and day["events"] == []
    assert len(day["tasks"]) == 6
    assert day["summary"] == {
        "planned": 6,
        "done": 3,
        "achieved": 2,
        "partial": 1,
        "missed": 1,
        "skipped": 1,
        "open": 1,
        "score": round(2.5 / 5, 4),
    }
    assert day["diary"]["body"] == "a day"
    assert [r["reference"] for r in day["readings"]] == ["John 1"]
    assert day["learned"] == {"reviewed": 1}


def test_day_for_another_date_is_empty_and_not_today(env) -> None:
    _, client, _ = env
    day = client.get("/api/days/2026-01-01").json()
    assert day["is_today"] is False and day["tasks"] == [] and day["diary"] is None
    assert day["summary"]["planned"] == 0 and day["summary"]["score"] is None


def test_day_tasks_ordered_by_due_time_then_created(env) -> None:
    _, client, clock = env
    late = make(client, "late", plan_date="2026-11-25", due="2026-11-25 18:00")
    clock.advance(minutes=1)
    none = make(client, "no-due", plan_date="2026-11-25")
    clock.advance(minutes=1)
    early = make(client, "early", plan_date="2026-11-25", due="2026-11-25 08:00")
    titles = [t["id"] for t in client.get("/api/days/2026-11-25").json()["tasks"]]
    assert titles == [early["id"], late["id"], none["id"]]


def test_invalid_dates_are_400(env) -> None:
    _, client, _ = env
    assert client.get("/api/days/yesterday").status_code == 400
    assert client.get("/api/days/range", params={"from": "2026-11-01"}).status_code == 400
    assert client.get("/api/days/range", params={"from": "x", "to": "y"}).status_code == 400
    assert client.post("/api/days/nope/carry-over").status_code == 400
    assert client.post("/api/days/2026-11-25/carry-over", json={"to": "bad"}).status_code == 400


def test_day_events_when_calendar_connected(tmp_path, monkeypatch) -> None:
    from tests.sync_support import ALL_SCOPES

    container, _ = build_sync_app(tmp_path, Clock(NOW), scopes=ALL_SCOPES)
    container.days._events = lambda tmin, tmax: [  # noqa: SLF001
        {"id": "e1", "title": "Standup", "startsAt": "2026-11-25T09:00:00Z", "location": ""}
    ]
    client = dashboard_client(container, tmp_path, monkeypatch)
    day = client.get("/api/days/2026-11-25").json()
    assert day["calendar_connected"] is True
    assert day["events"][0]["title"] == "Standup"

    def boom(tmin, tmax):
        raise RuntimeError("calendar down")

    container.days._events = boom  # noqa: SLF001
    assert client.get("/api/days/2026-11-25").json()["events"] == []


def test_range_rows_only_for_days_with_tasks(env) -> None:
    _, client, _ = env
    seed_day(client, "2026-11-20", ["achieved", "missed"])
    seed_day(client, "2026-11-22", ["skipped"], 2)
    rows = client.get("/api/days/range", params={"from": "2026-11-19", "to": "2026-11-25"}).json()
    assert [r["date"] for r in rows] == ["2026-11-20", "2026-11-22"]
    assert rows[0] == {
        "date": "2026-11-20",
        "planned": 2,
        "achieved": 1,
        "partial": 0,
        "missed": 1,
        "skipped": 0,
        "open": 0,
        "score": 0.5,
    }
    assert rows[1]["open"] == 2 and rows[1]["skipped"] == 1 and rows[1]["score"] == 0.0


def test_range_limit_is_62_days(env) -> None:
    _, client, _ = env
    ok = client.get("/api/days/range", params={"from": "2026-01-01", "to": "2026-03-03"})
    assert ok.status_code == 200  # exactly 62 days
    too_long = client.get("/api/days/range", params={"from": "2026-01-01", "to": "2026-03-04"})
    assert too_long.status_code == 400
    assert (
        client.get("/api/days/range", params={"from": "2026-03-04", "to": "2026-01-01"}).status_code
        == 400
    )


def test_stats_streak_week_and_month(env) -> None:
    _, client, _ = env  # 2026-11-25 is a Wednesday
    seed_day(client, "2026-11-25", ["achieved", "achieved"])
    seed_day(client, "2026-11-24", ["achieved", "achieved", "partial"])  # 2.5 / 3 = 0.83
    seed_day(client, "2026-11-23", ["achieved"])
    seed_day(client, "2026-11-22", ["achieved", "missed", "missed"])  # breaks the streak
    seed_day(client, "2026-11-02", ["achieved", "missed"])
    stats = client.get("/api/days/stats").json()
    assert stats["streak_days"] == 3
    assert stats["week"] == {
        "planned": 6,
        "achieved": 5,
        "partial": 1,
        "missed": 0,
        "rate": round(5.5 / 6, 4),
    }  # Mon 23rd .. Wed 25th
    assert stats["month"]["planned"] == 11 and stats["month"]["rate"] == round(7.5 / 11, 4)


def test_stats_streak_waits_for_an_unfinished_today(env) -> None:
    _, client, _ = env
    seed_day(client, "2026-11-25", ["achieved"], 1)
    seed_day(client, "2026-11-24", ["achieved"])
    seed_day(client, "2026-11-23", ["achieved", "achieved"])
    stats = client.get("/api/days/stats").json()
    assert stats["streak_days"] == 2
    assert stats["week"]["rate"] == 0.8  # the open task is still in the denominator


def test_stats_empty_workspace(env) -> None:
    _, client, _ = env
    assert client.get("/api/days/stats").json() == {
        "streak_days": 0,
        "week": {"planned": 0, "achieved": 0, "partial": 0, "missed": 0, "rate": None},
        "month": {"planned": 0, "achieved": 0, "partial": 0, "missed": 0, "rate": None},
    }


def test_owner_timezone_decides_today(tmp_path, monkeypatch) -> None:
    clock = Clock(utc(2026, 11, 25, 22, 30))  # already the 26th in Nairobi
    container, _ = build_sync_app(tmp_path, clock, scopes=None, timezone="Africa/Nairobi")
    client = dashboard_client(container, tmp_path, monkeypatch)
    assert make(client)["plan_date"] == "2026-11-26"
    assert client.get("/api/days/2026-11-26").json()["is_today"] is True
    assert client.get("/api/today").json()["day"]["date"] == "2026-11-26"


# -- carry-over --------------------------------------------------------------------------------


def test_carry_over_moves_only_open_tasks(env) -> None:
    _, client, _ = env
    open_task = make(client, "open", plan_date="2026-11-25")
    progress = make(client, "progress", plan_date="2026-11-25")
    client.patch(f"/api/tasks/{progress['id']}", json={"status": "in_progress"})
    blocked = make(client, "blocked", plan_date="2026-11-25")
    client.patch(f"/api/tasks/{blocked['id']}", json={"status": "in_progress"})
    client.patch(f"/api/tasks/{blocked['id']}", json={"status": "blocked"})
    done = make(client, "done", plan_date="2026-11-25")
    client.post(f"/api/tasks/{done['id']}/complete", json={"outcome": "achieved"})
    cancelled = make(client, "cancelled", plan_date="2026-11-25")
    client.post(f"/api/tasks/{cancelled['id']}/complete", json={"outcome": "missed"})
    resp = client.post("/api/days/2026-11-25/carry-over", json={})
    body = resp.json()
    assert resp.status_code == 200
    assert body["moved"] == 3 and body["to"] == "2026-11-26"
    assert set(body["task_ids"]) == {open_task["id"], progress["id"], blocked["id"]}
    for task_id, expected in [
        (open_task["id"], "2026-11-26"),
        (done["id"], "2026-11-25"),
        (cancelled["id"], "2026-11-25"),
    ]:
        assert client.get(f"/api/tasks/{task_id}").json()["plan_date"] == expected
    assert client.post("/api/days/2026-11-25/carry-over").json()["moved"] == 0  # nothing left


def test_carry_over_to_a_given_day_and_without_body(env) -> None:
    _, client, _ = env
    task = make(client, plan_date="2026-11-25")
    body = client.post("/api/days/2026-11-25/carry-over", json={"to": "2026-12-01"}).json()
    assert body == {"moved": 1, "to": "2026-12-01", "task_ids": [task["id"]]}
    again = make(client, plan_date="2026-11-25")
    assert client.post("/api/days/2026-11-25/carry-over").json()["task_ids"] == [again["id"]]


# -- today -------------------------------------------------------------------------------------


def test_today_has_day_block_with_next_task(env) -> None:
    _, client, _ = env
    empty = client.get("/api/today").json()["day"]
    assert empty["date"] == "2026-11-25" and empty["next_task"] is None
    assert empty["summary"]["planned"] == 0
    later = make(client, "later", due="2026-11-25 18:00")
    sooner = make(client, "sooner", due="2026-11-25 15:00")
    day = client.get("/api/today").json()["day"]
    assert day["next_task"] == {"id": sooner["id"], "title": "sooner", "due_at": sooner["due_at"]}
    client.post(f"/api/tasks/{sooner['id']}/complete", json={})
    client.post(f"/api/tasks/{later['id']}/complete", json={})
    day = client.get("/api/today").json()["day"]
    assert day["next_task"] is None and day["summary"]["achieved"] == 2


# -- tools through the real registry -----------------------------------------------------------


def test_task_create_tool_with_target_and_plan_date(env) -> None:
    container, _, _ = env
    result, out = call(
        container,
        "task_create",
        title="Push-ups",
        target_value=30,
        target_unit="push-ups",
        plan_date="2026-11-27",
    )
    assert result.ok and out["plan_date"] == "2026-11-27" and out["target_value"] == 30.0
    bad, _ = call(container, "task_create", title="x", plan_date="soon")
    assert not bad.ok


def test_task_complete_tool_by_query_completes_exactly_one(env) -> None:
    container, client, _ = env
    task = make(client, "Do 30 push-ups", target_value=30)
    make(client, "Read a book")
    result, out = call(container, "task_complete", title_query="PUSH", actual_value=30)
    assert result.ok and out["completed"] is True and out["outcome"] == "achieved"
    stored = client.get(f"/api/tasks/{task['id']}").json()
    assert stored["status"] == "done" and stored["actual_value"] == 30.0


def test_task_complete_tool_ambiguity_changes_nothing(env) -> None:
    container, client, _ = env
    a = make(client, "Run in the morning")
    b = make(client, "Run the report")
    result, out = call(container, "task_complete", title_query="run")
    assert result.ok and out["completed"] is False and out["reason"] == "ambiguous"
    assert {c["id"] for c in out["candidates"]} == {a["id"], b["id"]}
    assert result.result_type == "task_candidates"
    for task in (a, b):
        assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "planned"
    none, out = call(container, "task_complete", title_query="swim")
    assert out["completed"] is False and out["reason"] == "no_match" and out["candidates"] == []


def test_task_complete_tool_only_matches_open_tasks_of_today(env) -> None:
    container, client, _ = env
    make(client, "Stretch", plan_date="2026-11-24")  # yesterday
    finished = make(client, "Stretch again")
    client.post(f"/api/tasks/{finished['id']}/complete", json={})
    _, out = call(container, "task_complete", title_query="stretch")
    assert out["completed"] is False and out["reason"] == "no_match"


def test_task_complete_tool_by_id_and_ownership(env) -> None:
    container, client, _ = env
    task = make(client, "Pay rent")
    _, out = call(container, "task_complete", task_id=task["id"], outcome="skipped", note="later")
    assert out["completed"] is True and out["outcome"] == "skipped"
    stolen = ToolContext(user_id="someone-else", session_id="s", origin="cli")
    res = container.registry.execute(
        ToolCall(id="c", name="task_complete", arguments={"task_id": task["id"]}), stolen
    )
    assert not res.ok
    missing, _ = call(container, "task_complete")
    assert not missing.ok  # needs task_id or title_query


def test_day_summary_tool(env) -> None:
    container, client, _ = env
    seed_day(client, "2026-11-25", ["achieved", "missed"], 1)
    result, out = call(container, "day_summary")
    assert result.ok and result.result_type == "day_summary"
    assert out["counts"]["planned"] == 3 and out["counts"]["open"] == 1
    assert "1 of 3 done" in out["summary"] and len(out["tasks"]) == 3
    _, other = call(container, "day_summary", date="2026-01-01")
    assert other["counts"]["planned"] == 0 and "no tasks" in other["summary"]


def test_day_carry_over_tool_is_prepare_and_moves_open_tasks(env) -> None:
    container, client, _ = env
    spec = next(s for s in container.registry.specs() if s.name == "day_carry_over")
    assert spec.access_kind == "prepare"
    task = make(client)
    result, out = call(container, "day_carry_over")
    assert out["moved"] == 1 and out["task_ids"] == [task["id"]]
    assert client.get(f"/api/tasks/{task['id']}").json()["plan_date"] == "2026-11-26"


def test_tool_access_kinds(env) -> None:
    container, _, _ = env
    kinds = {s.name: s.access_kind for s in container.registry.specs()}
    assert kinds["task_complete"] == "prepare" and kinds["day_summary"] == "read"
    assert kinds["drive_sync_push"] == "execute" and kinds["task_calendar_sync"] == "execute"
    assert kinds["drive_sync_status"] == "read"


# -- export and wipe ---------------------------------------------------------------------------


def test_export_includes_new_task_fields_and_sync_data(env) -> None:
    container, client, _ = env
    task = make(client, target_value=30, target_unit="push-ups")
    client.post(f"/api/tasks/{task['id']}/complete", json={"actual_value": 12, "note": "ok"})
    container.drive_sync.update_settings(OWNER, enabled=True)
    data = client.get("/api/export").json()
    row = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert row["plan_date"] == "2026-11-25" and row["outcome"] == "partial"
    assert (row["target_value"], row["actual_value"], row["outcome_note"]) == (30.0, 12.0, "ok")
    assert "calendar_event_id" in row and "calendar_synced_at" in row
    assert "drive_links" in data
    drive = next(s for s in data["sync_settings"] if s["service"] == "drive")
    assert drive["enabled"] is True


def test_wipe_clears_sync_data(env) -> None:
    container, client, _ = env
    container.drive_sync.update_settings(OWNER, enabled=True)
    token = client.post("/api/workspace/wipe/token").json()
    resp = client.post(
        "/api/workspace/wipe",
        json={"token": token["token"], "confirm_phrase": token["confirm_phrase"]},
    )
    assert resp.status_code == 200, resp.text
    assert "drive_links" in resp.json()["deleted"]
    assert container.drive_sync.get_settings(OWNER).enabled is False


def test_clock_helpers_are_controlled() -> None:
    clock = Clock(NOW)
    clock.advance(hours=1)
    assert clock() == NOW + timedelta(hours=1)
