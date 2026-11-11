"""MEM-06: redaction refuses credentials, government IDs and card numbers."""

from __future__ import annotations

import pytest

from personal_agent.domain.memory import assert_storable, redaction_reason


@pytest.mark.parametrize(
    "content",
    [
        "Prefers morning meetings",
        "Dawit is my colleague at work",
        "Timezone Africa/Addis_Ababa",
        "Routine: gym on Tuesdays",
    ],
)
def test_safe_content_allowed(content: str):
    assert redaction_reason(content) is None
    assert assert_storable(content) == content


@pytest.mark.parametrize(
    "content",
    [
        "My card is 4111 1111 1111 1111",
        "visa 5500000000000004",
        "SSN 123-45-6789",
        "password: hunter2-secret",
        "api_key sk-abcdefghijklmnopqrstuvwxyz",
        "passport number AB1234567 for travel",
    ],
)
def test_sensitive_content_blocked(content: str):
    assert redaction_reason(content) is not None
    with pytest.raises(ValueError):
        assert_storable(content)
