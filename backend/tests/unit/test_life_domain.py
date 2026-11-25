"""Life modules: pure rules (Leitner, streaks, validation, magic bytes, templates)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from personal_agent.domain.life import (
    LifeError,
    LifeTooLarge,
    clean_learn_item,
    clean_note_create,
    clean_tags,
    leitner_review,
    magic_matches,
    reading_templates,
    streak_days,
)

TODAY = date(2026, 11, 25)


@pytest.mark.parametrize(
    ("box", "result", "new_box", "delta"),
    [
        (0, "know", 1, timedelta(days=1)),
        (1, "know", 2, timedelta(days=3)),
        (2, "know", 3, timedelta(days=7)),
        (3, "know", 4, timedelta(days=14)),
        (4, "know", 5, timedelta(days=30)),
        (5, "know", 5, timedelta(days=30)),
        (4, "again", 0, timedelta(minutes=10)),
        (0, "again", 0, timedelta(minutes=10)),
    ],
)
def test_leitner_intervals(box, result, new_box, delta) -> None:
    now = datetime(2026, 11, 25, 9, 0, tzinfo=UTC)
    assert leitner_review(box, result, now) == (new_box, now + delta)


def test_leitner_rejects_unknown_result() -> None:
    with pytest.raises(LifeError):
        leitner_review(0, "maybe", datetime.now(UTC))


def test_streak_counts_back_from_today_or_yesterday() -> None:
    day = timedelta(days=1)
    assert streak_days(set(), TODAY) == 0
    assert streak_days({TODAY}, TODAY) == 1
    assert streak_days({TODAY, TODAY - day, TODAY - 2 * day}, TODAY) == 3
    # Yesterday rule: not written today yet, the streak is still alive.
    assert streak_days({TODAY - day, TODAY - 2 * day}, TODAY) == 2
    # A gap of one full day breaks it.
    assert streak_days({TODAY - 2 * day, TODAY - 3 * day}, TODAY) == 0
    # A gap inside the run stops the count.
    assert streak_days({TODAY, TODAY - 2 * day}, TODAY) == 1


def test_magic_bytes() -> None:
    assert magic_matches("image/png", b"\x89PNG\r\n\x1a\nxxxx")
    assert not magic_matches("image/png", b"\xff\xd8\xff\xe0")
    assert magic_matches("image/jpeg", b"\xff\xd8\xff\xe0")
    assert magic_matches("image/gif", b"GIF89a....")
    assert magic_matches("image/webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ")
    assert not magic_matches("image/webp", b"RIFF\x00\x00\x00\x00WAVEfmt ")
    assert magic_matches("application/pdf", b"%PDF-1.7")
    assert not magic_matches("application/pdf", b"<html>")
    assert magic_matches("text/plain", b"hello")
    assert not magic_matches("text/plain", b"he\x00llo")


def test_tags_are_lowercased_deduped_and_limited() -> None:
    assert clean_tags([" Work ", "work", "Home", ""]) == ["work", "home"]
    with pytest.raises(LifeError):
        clean_tags([f"t{i}" for i in range(11)])
    with pytest.raises(LifeError):
        clean_tags(["x" * 31])


def test_note_rules() -> None:
    note = clean_note_create({"kind": "note", "body": "# Plan\nthings"}, today=TODAY)
    assert note["title"] == "Plan" and note["entry_date"] is None
    diary = clean_note_create({"kind": "diary", "body": "hi", "mood": "good"}, today=TODAY)
    assert diary["entry_date"] == TODAY
    with pytest.raises(LifeError):
        clean_note_create({"kind": "note", "body": "x", "mood": "good"}, today=TODAY)
    with pytest.raises(LifeError):
        clean_note_create({"kind": "diary", "body": "x", "mood": "ecstatic"}, today=TODAY)
    with pytest.raises(LifeError):
        clean_note_create({"kind": "note", "body": "x" * 50_001}, today=TODAY)
    with pytest.raises(LifeError):
        clean_note_create({"kind": "note", "title": "", "body": "  "}, today=TODAY)
    assert issubclass(LifeTooLarge, LifeError)


def test_learn_item_validation() -> None:
    item = clean_learn_item({"term": " hola ", "meaning": "hello"})
    assert item["term"] == "hola" and item["language"] == "en" and item["kind"] == "word"
    with pytest.raises(LifeError):
        clean_learn_item({"term": "", "meaning": "x"})
    with pytest.raises(LifeError):
        clean_learn_item({"term": "a", "meaning": "x" * 1001})
    with pytest.raises(LifeError):
        clean_learn_item({"term": "a", "meaning": "x", "kind": "sentence"})


def test_reading_templates_expand_to_ordered_references() -> None:
    templates = reading_templates()
    john = templates["gospel-of-john-21"].items
    assert john[0] == "John 1" and john[-1] == "John 21" and len(john) == 21
    assert len(templates["psalms-30"].items) == 30
    assert len(templates["proverbs-31"].items) == 31
    nt = templates["new-testament-90"].items
    assert len(nt) == 90
    assert (
        nt[0].startswith("Matthew 1")
        and nt[-1].endswith("Revelation 20-22")
        or "Revelation" in nt[-1]
    )
