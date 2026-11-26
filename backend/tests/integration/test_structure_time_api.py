"""Projects, subtasks, dependencies, time tracking and learning paths (roadmap P2-1..P2-3)."""

from __future__ import annotations

import pytest

from tests.integration.test_tasks_api import _client


@pytest.fixture
def client(tmp_path):
    return _client(tmp_path)


def _task(client, **body):
    r = client.post("/api/tasks", json={"title": "t", **body})
    assert r.status_code == 201, r.text
    return r.json()


def test_subtasks_progress_and_one_level_only(client):
    parent = _task(client, title="Launch", project="Site")
    a = _task(client, title="Write copy", parent_id=parent["id"])
    _task(client, title="Design", parent_id=parent["id"])
    client.post(f"/api/tasks/{a['id']}/complete", json={"outcome": "achieved"})
    got = client.get(f"/api/tasks/{parent['id']}").json()
    assert got["subtasks"] == {"done": 1, "total": 2}
    deeper = client.post("/api/tasks", json={"title": "x", "parent_id": a["id"]})
    assert deeper.status_code == 400 and "one level" in deeper.json()["detail"]
    assert client.post("/api/tasks", json={"title": "x", "parent_id": "nope"}).status_code == 400
    # A task that already has subtasks cannot itself become a subtask.
    other = _task(client, title="Other")
    bad = client.patch(f"/api/tasks/{parent['id']}", json={"parent_id": other["id"]})
    assert bad.status_code == 400


def test_blocked_by_flag_and_loop_rejected(client):
    first = _task(client, title="Get approval")
    second = _task(client, title="Build", blocked_by=[first["id"]])
    assert client.get(f"/api/tasks/{second['id']}").json()["blocked"] is True
    client.post(f"/api/tasks/{first['id']}/complete", json={"outcome": "achieved"})
    assert client.get(f"/api/tasks/{second['id']}").json()["blocked"] is False
    loop = client.patch(f"/api/tasks/{first['id']}", json={"blocked_by": [second["id"]]})
    assert loop.status_code == 400 and "loop" in loop.json()["detail"]
    own = client.patch(f"/api/tasks/{first['id']}", json={"blocked_by": [first["id"]]})
    assert own.status_code == 400


def test_project_progress_rename_and_conflict(client):
    p = client.post("/api/projects", json={"name": "Website", "deadline": "2099-01-01"})
    assert p.status_code == 201, p.text
    assert client.post("/api/projects", json={"name": "Website"}).status_code == 409
    t1 = _task(client, title="A", project="Website")
    _task(client, title="B", project="Website")
    client.post(f"/api/tasks/{t1['id']}/complete", json={"outcome": "achieved"})
    view = client.get("/api/projects").json()[0]
    assert view["tasks"]["done"] == 1 and view["tasks"]["total"] == 2 and view["progress_pct"] == 50
    assert view["days_left"] > 0
    renamed = client.patch(f"/api/projects/{view['id']}", json={"name": "Site v2"})
    assert renamed.status_code == 200
    assert client.get(f"/api/tasks/{t1['id']}").json()["project"] == "Site v2"
    assert client.patch(f"/api/projects/{view['id']}", json={"nope": 1}).status_code == 422
    assert client.delete(f"/api/projects/{view['id']}").status_code == 204


def test_timer_single_running_manual_and_summary(client):
    task = _task(client, title="Study", project="Learning")
    started = client.post("/api/time/start", json={"task_id": task["id"]})
    assert started.status_code == 201 and started.json()["project"] == "Learning"
    again = client.post("/api/time/start", json={"project": "Admin"})
    assert again.status_code == 201
    entries = client.get("/api/time/entries").json()
    assert sum(1 for e in entries if e["running"]) == 1  # only the newest timer runs
    assert client.get("/api/time/running").json()["entry"]["project"] == "Admin"
    assert client.post("/api/time/stop").status_code == 200
    assert client.post("/api/time/stop").status_code == 400

    manual = client.post("/api/time/entries", json={"minutes": 90, "task_id": task["id"]})
    assert manual.status_code == 201 and manual.json()["minutes"] == 90
    for bad in ({"minutes": 0}, {"minutes": 5000}, {"minutes": 5, "day": "2999-01-01"}):
        assert client.post("/api/time/entries", json=bad).status_code == 400
    summary = client.get("/api/time/summary").json()
    assert summary["total_minutes"] >= 90
    assert summary["by_project"][0] == {"project": "Learning", "minutes": 90}
    assert summary["by_task"][0]["task_id"] == task["id"]
    entry_id = manual.json()["id"]
    assert client.delete(f"/api/time/entries/{entry_id}").status_code == 204
    assert client.delete(f"/api/time/entries/{entry_id}").status_code == 404


def test_learning_path_milestones_and_hours(client):
    goal = client.post(
        "/api/goals",
        json={
            "title": "AWS certification",
            "kind": "certification",
            "target_hours": 40,
            "milestones": [{"title": "Core services"}, {"title": "Networking"}, "Mock exam"],
        },
    )
    assert goal.status_code == 201, goal.text
    body = goal.json()
    assert body["kind"] == "certification" and len(body["milestones"]) == 3
    assert body["progress"] == 0 and body["studied_hours"] == 0
    milestones = body["milestones"]
    milestones[0]["done"] = True
    patched = client.patch(f"/api/goals/{body['id']}", json={"milestones": milestones})
    assert patched.status_code == 200 and round(patched.json()["progress"], 2) == 0.33
    client.post("/api/time/entries", json={"minutes": 120, "goal_id": body["id"]})
    assert client.get(f"/api/goals/{body['id']}").json()["studied_hours"] == 2.0
    bad_kind = client.post("/api/goals", json={"title": "x", "kind": "hobby"})
    assert bad_kind.status_code == 422
