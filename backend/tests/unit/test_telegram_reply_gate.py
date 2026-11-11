from personal_agent.application.services.telegram_reply_gate import needs_reply


def test_questions_and_requests_need_reply():
    assert needs_reply("Can you check my email?") is True
    assert needs_reply("please remind me tomorrow") is True
    assert needs_reply("What is on my calendar") is True
    assert needs_reply("send a message to mom") is True
    assert needs_reply("help me with this") is True


def test_casual_noise_is_silent():
    assert needs_reply("ok") is False
    assert needs_reply("thanks") is False
    assert needs_reply("lol") is False
    assert needs_reply("👍") is False
    assert needs_reply("") is False
    assert needs_reply("   ") is False


def test_longer_substantive_message_needs_reply():
    assert needs_reply("I have a meeting later and need notes prepared for it") is True
