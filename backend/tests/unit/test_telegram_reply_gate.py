from personal_agent.application.services.telegram_reply_gate import (
    is_private_owner_chat,
    message_mentions_bot,
    needs_reply,
)


def test_non_english_substantive_messages_need_reply():
    assert needs_reply("Je dois préparer une note pour demain") is True
    assert needs_reply("Necesito ayuda con el correo de hoy") is True
    assert needs_reply("أحتاج إلى تذكير غداً صباحاً") is True


def test_multilingual_acks_and_emoji_are_silent():
    assert needs_reply("merci") is False
    assert needs_reply("gracias") is False
    assert needs_reply("شكرا") is False
    assert needs_reply("👍") is False
    assert needs_reply("🙏😊") is False
    assert needs_reply("") is False
    assert needs_reply("   ") is False
    assert needs_reply("ok") is False
    assert needs_reply("thanks") is False


def test_english_questions_still_need_reply():
    assert needs_reply("Can you check my email?") is True
    assert needs_reply("please remind me tomorrow") is True
    assert needs_reply("I have a meeting later and need notes prepared for it") is True


def test_private_owner_chat_helper():
    assert is_private_owner_chat(chat_id=42, sender_id=42) is True
    assert is_private_owner_chat(chat_id=-100, sender_id=42) is False
    assert is_private_owner_chat(chat_id=42, sender_id=99) is False


def test_mention_detection():
    text = "hey @aura_bot please help"
    assert message_mentions_bot(text, bot_username="aura_bot", entities=[]) is True
    assert message_mentions_bot("hello", bot_username="aura_bot", entities=[]) is False
    entities = [{"type": "mention", "offset": 4, "length": 9}]
    assert message_mentions_bot("hey @aura_bot", bot_username="aura_bot", entities=entities) is True
