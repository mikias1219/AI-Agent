from personal_agent.presentation.web.app import should_autostart_telegram


def test_should_autostart_requires_worker_and_allowlist():
    assert should_autostart_telegram(object(), frozenset({1})) is True
    assert should_autostart_telegram(object(), frozenset()) is False
    assert should_autostart_telegram(None, frozenset({1})) is False
    assert should_autostart_telegram(None, frozenset()) is False
