"""Signed OAuth state: only a value minted with the server secret is accepted, once."""

from __future__ import annotations

import pytest

from personal_agent.application.security.oauth_state import (
    STATE_TTL_SECONDS,
    OAuthStateError,
    UsedStates,
    issue_state,
    verify_state,
)

SECRET = "a-server-secret-that-is-long-enough"


def test_round_trip_keeps_read_only_flag():
    for read_only in (True, False):
        state = issue_state(SECRET, read_only=read_only, now=1000)
        assert verify_state(SECRET, state, now=1001).read_only is read_only


def test_each_state_is_unique():
    assert issue_state(SECRET, read_only=True) != issue_state(SECRET, read_only=True)


@pytest.mark.parametrize("value", ["", "ro=0", "ro=1", "v1.0.9999999999.nonce", "a.b.c.d.e"])
def test_unsigned_or_legacy_values_are_rejected(value):
    with pytest.raises(OAuthStateError):
        verify_state(SECRET, value)


def test_state_signed_with_another_secret_is_rejected():
    state = issue_state("some-other-secret-entirely-different", read_only=False)
    with pytest.raises(OAuthStateError):
        verify_state(SECRET, state)


def test_changing_the_read_only_flag_breaks_the_signature():
    state = issue_state(SECRET, read_only=True, now=1000)
    version, _flag, expires, nonce, signature = state.split(".")
    tampered = ".".join([version, "0", expires, nonce, signature])
    with pytest.raises(OAuthStateError):
        verify_state(SECRET, tampered, now=1001)


def test_expired_state_is_rejected():
    state = issue_state(SECRET, read_only=True, now=1000)
    verify_state(SECRET, state, now=1000 + STATE_TTL_SECONDS)
    with pytest.raises(OAuthStateError):
        verify_state(SECRET, state, now=1000 + STATE_TTL_SECONDS + 1)


def test_state_can_be_claimed_only_once():
    used = UsedStates()
    state = verify_state(SECRET, issue_state(SECRET, read_only=True, now=1000), now=1001)
    used.claim(state, now=1001)
    with pytest.raises(OAuthStateError):
        used.claim(state, now=1002)


def test_missing_secret_never_issues_or_verifies():
    with pytest.raises(OAuthStateError):
        issue_state("", read_only=True)
    with pytest.raises(OAuthStateError):
        verify_state("", "v1.1.9999999999.nonce.sig")
