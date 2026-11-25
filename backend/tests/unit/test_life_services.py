"""Life services with a controlled clock: streaks, timezones, nudges and notification gating."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from personal_agent.app.container import AppContainer, build_app
from personal_agent.config.settings import Settings
from personal_agent.domain.life import LifeConflict
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider

BACKEND = Path(__file__).resolve().parents[2]
OWNER = "dashboard"


class Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def _app(tmp_path, clock: Clock) -> AppContainer:
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'svc.db'}",
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    return build_app(settings=settings, provider=FakeProvider(), clock=clock)


@pytest.fixture()
def clock() -> Clock:
    return Clock(datetime(2026, 11, 25, 12, 0, tzinfo=UTC))


@pytest.fixture()
def app(tmp_path, clock) -> AppContainer:
    return _app(tmp_path, clock)


def test_diary_streak_yesterday_rule_and_timezone(app, clock) -> None:
    for days_ago in (3, 2, 1):  # not written today yet: streak still counts through yesterday
        day = (clock.now - timedelta(days=days_ago)).date().isoformat()
        app.notes.create(OWNER, {"kind": "diary", "body": "x", "entry_date": day})
    stats = app.notes.stats(OWNER)
    assert stats == {
        "notes": 0,
        "diary_entries": 3,
        "diary_streak_days": 3,
        "wrote_diary_today": False,
    }
    app.notes.create(OWNER, {"kind": "diary", "body": "today"})
    assert app.notes.stats(OWNER)["diary_streak_days"] == 4

    # The owner's timezone decides what "today" is: 23:00 UTC is already tomorrow in Auckland.
    clock.now = datetime(2026, 11, 25, 23, 0, tzinfo=UTC)
    app.profiles.update(OWNER, timezone="Pacific/Auckland")
    assert app.notes.stats(OWNER)["wrote_diary_today"] is False
    assert app.notes.stats(OWNER)["diary_streak_days"] == 4  # yesterday rule keeps it alive


def test_learning_streak_and_due_after_leitner(app, clock) -> None:
    created, _ = app.learn.create_many(OWNER, [{"term": "a", "meaning": "b"}])
    item = created[0]
    app.learn.review(OWNER, item.id, "know")
    assert app.learn.stats(OWNER)["due"] == 0
    clock.now += timedelta(days=1, minutes=1)
    assert app.learn.stats(OWNER)["due"] == 1
    assert app.learn.stats(OWNER)["streak_days"] == 1  # reviewed yesterday, still alive
    app.learn.review(OWNER, item.id, "know")
    assert app.learn.stats(OWNER)["streak_days"] == 2
    clock.now += timedelta(days=3)  # nothing reviewed for two full days
    assert app.learn.stats(OWNER)["streak_days"] == 0


def test_reading_streak_and_agent_logging(app, clock) -> None:
    app.reading.create_plan(OWNER, {"name": "J", "items": ["John 1", "John 2"]})
    log, plan = app.reading.log_reference(OWNER, " john   1 ", "ok")
    assert plan is not None and plan.position == 1 and log.reference == "John 1"
    other, none_plan = app.reading.log_reference(OWNER, "Psalm 23")
    assert none_plan is None and other.plan_id is None  # not the plan's next: logged only
    assert app.reading.active_plan(OWNER).next == "John 2"  # type: ignore[union-attr]
    clock.now += timedelta(days=1)
    stats = app.reading.stats(OWNER)
    assert stats["read_today"] is False and stats["streak_days"] == 1


def test_diary_append_does_not_fail_on_existing_entry(app) -> None:
    first, appended = app.notes.diary_append(OWNER, "Morning", mood="good")
    assert appended is False
    second, appended = app.notes.diary_append(OWNER, "Evening")
    assert appended is True and second.id == first.id
    assert second.body == "Morning\n\nEvening" and second.mood == "good"
    with pytest.raises(LifeConflict):
        app.notes.create(OWNER, {"kind": "diary", "body": "dup"})


def test_owner_scoping(app) -> None:
    note = app.notes.create("someone-else", {"kind": "note", "body": "private"})
    assert app.notes.list(OWNER) == []
    with pytest.raises(Exception):  # noqa: B017,PT011 - LifeNotFound
        app.notes.get(OWNER, note.id)


# -- notification prefs are honoured by real producers -----------------------------------------


def _enable(app, **patch) -> None:
    app.notifications.update(OWNER, patch)


def _open_titles(app) -> list[str]:
    return [s.title for s in app.suggestions.open(OWNER)]


def test_learning_nudge_is_delivered_in_app_and_telegram_once(app, clock) -> None:
    sent: list[str] = []
    app.scheduler._telegram_send = sent.append  # noqa: SLF001
    app.learn.create_many(OWNER, [{"term": "hola", "meaning": "hello"}])
    _enable(app, daily_briefing=False, learning_daily=True, learning_time="12:00")
    app.scheduler.tick()
    app.scheduler.tick()  # idempotent for the day
    assert len(sent) == 1 and "due for review" in sent[0] and "hola" in sent[0]
    titles = _open_titles(app)
    assert len(titles) == 1 and "due for review" in titles[0]


def test_nudge_off_or_nothing_to_nudge_sends_nothing(app, clock) -> None:
    sent: list[str] = []
    app.scheduler._telegram_send = sent.append  # noqa: SLF001
    _enable(app, daily_briefing=False, learning_daily=False, learning_time="12:00")
    app.learn.create_many(OWNER, [{"term": "hola", "meaning": "hello"}])
    app.scheduler.tick()
    assert sent == [] and _open_titles(app) == []  # flag off
    _enable(app, learning_daily=True)
    app.learn.review(OWNER, app.learn.list(OWNER)[0].id, "know")  # nothing due any more
    app.scheduler.tick()
    assert sent == [] and _open_titles(app) == []


def test_reading_and_diary_nudges_use_real_state(app, clock) -> None:
    sent: list[str] = []
    app.scheduler._telegram_send = sent.append  # noqa: SLF001
    app.reading.create_plan(OWNER, {"name": "John", "template": "gospel-of-john-21"})
    _enable(
        app,
        daily_briefing=False,
        reading_daily=True,
        reading_time="12:00",
        diary_nudge=True,
        diary_time="12:00",
        channels={"telegram": False},
    )
    app.scheduler.tick()
    assert sent == []  # Telegram channel off
    titles = _open_titles(app)
    assert any("John 1" in t for t in titles) and any("diary" in t for t in titles)


def test_diary_nudge_skipped_when_already_written(app) -> None:
    app.notes.create(OWNER, {"kind": "diary", "body": "done"})
    _enable(app, daily_briefing=False, diary_nudge=True, diary_time="12:00")
    app.scheduler.tick()
    assert _open_titles(app) == []


def test_in_app_channel_off_skips_suggestion(app) -> None:
    sent: list[str] = []
    app.scheduler._telegram_send = sent.append  # noqa: SLF001
    app.learn.create_many(OWNER, [{"term": "hola", "meaning": "hello"}])
    _enable(
        app,
        daily_briefing=False,
        learning_daily=True,
        learning_time="12:00",
        channels={"in_app": False},
    )
    app.scheduler.tick()
    assert len(sent) == 1 and _open_titles(app) == []


def test_quiet_hours_block_external_nudge_but_not_in_app(app) -> None:
    sent: list[str] = []
    app.scheduler._telegram_send = sent.append  # noqa: SLF001
    app.learn.create_many(OWNER, [{"term": "hola", "meaning": "hello"}])
    _enable(
        app,
        daily_briefing=False,
        learning_daily=True,
        learning_time="12:00",
        quiet_hours={"enabled": True, "start": "11:00", "end": "13:00"},
    )
    app.scheduler.tick()
    assert sent == [] and len(_open_titles(app)) == 1


def test_reminders_flag_gates_external_delivery(app, clock) -> None:
    sent: list[str] = []
    app.scheduler._telegram_send = sent.append  # noqa: SLF001
    _enable(app, daily_briefing=False, reminders=False)
    app.scheduler.create_reminder(
        text="call mum", remind_at=clock.now + timedelta(minutes=1), owner_user_id=OWNER
    )
    clock.now += timedelta(minutes=2)
    app.scheduler.tick()
    assert sent == []
    _enable(app, reminders=True)
    app.scheduler.create_reminder(
        text="call dad", remind_at=clock.now + timedelta(minutes=1), owner_user_id=OWNER
    )
    clock.now += timedelta(minutes=2)
    app.scheduler.tick()
    assert sent == ["call dad"]


def test_briefing_flag_disables_the_routine(app) -> None:
    _enable(app, daily_briefing=False)
    assert app.scheduler.enqueue_due_automations() == 0
    _enable(app, daily_briefing=True)
    assert app.scheduler.enqueue_due_automations() == 1


# -- migration ---------------------------------------------------------------------------------


def test_life_migration_up_and_down(tmp_path, monkeypatch) -> None:
    db = tmp_path / "mig.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")

    def tables() -> set[str]:
        with sqlite3.connect(db) as conn:
            return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def profile_cols() -> set[str]:
        with sqlite3.connect(db) as conn:
            return {r[1] for r in conn.execute("PRAGMA table_info(owner_profile)")}

    life = {
        "notes",
        "files",
        "profile_photos",
        "learn_items",
        "learn_reviews",
        "reading_plans",
        "reading_logs",
    }
    assert life <= tables()
    assert {"bio", "birthday", "notification_prefs", "created_at"} <= profile_cols()
    command.downgrade(cfg, "20261125_01")
    assert not (life & tables())
    assert not ({"bio", "birthday", "notification_prefs", "created_at"} & profile_cols())
    command.upgrade(cfg, "head")
    assert life <= tables()
