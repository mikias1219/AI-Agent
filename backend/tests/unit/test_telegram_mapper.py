"""Unit: Telegram payload parsing — strict, skip-what-you-don't-understand."""

from __future__ import annotations

from personal_agent.infrastructure.integrations.telegram.mapper import (
    TelegramIncoming,
    parse_update,
    parse_updates,
)


def _text_update(update_id=1, chat_id=42, sender_id=7, username="alice", text="hi"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": sender_id, "username": username},
            "text": text,
        },
    }


def test_parse_full_update():
    incoming = parse_update(_text_update(username="amy", text=" Hello "))
    assert incoming == TelegramIncoming(
        update_id=1, chat_id=42, sender_id=7, username="amy", text="Hello"
    )
    assert incoming.sender_key == "tg:7"


def test_missing_username_falls_back_to_numeric_key():
    update = _text_update()
    update["message"]["from"]["username"] = None
    assert parse_update(update).sender_key == "tg:7"


def test_non_text_content_is_skipped():
    raw = {
        "update_id": 2,
        "message": {"chat": {"id": 42}, "from": {"id": 7}, "sticker": {"emoji": "🎉"}},
    }
    assert parse_update(raw) is None


def test_edited_and_malformed_updates_are_skipped():
    assert parse_update({"update_id": 3, "edited_message": {"text": "late edit"}}) is None
    assert parse_update({"update_id": 4}) is None  # no message at all
    assert parse_update(None) is None  # type: ignore[arg-type] — loader tolerance
    assert parse_update("junk") is None  # type: ignore[arg-type]


def test_empty_text_is_skipped():
    assert parse_update(_text_update(text="   ")) is None


def test_parse_updates_drops_bad_but_keeps_good():
    batch = [_text_update(update_id=1, text="first"), {"update_id": 2}]
    parsed = parse_updates(batch)
    assert [p.update_id for p in parsed] == [1]

    batch = _text_update(update_id=9, chat_id=-100, text="group msg")
    assert parse_updates([batch])[0].chat_id == -100


def test_invalid_nested_payloads_and_numeric_ids_are_skipped():
    assert parse_update({"update_id": 1, "message": {"chat": "junk", "text": "hello"}}) is None
    malformed = _text_update()
    malformed["message"]["chat"]["id"] = "not-a-number"
    assert parse_update(malformed) is None


def test_username_change_does_not_change_identity():
    assert (
        parse_update(_text_update(username="old")).sender_key
        == parse_update(_text_update(username="new")).sender_key
    )
