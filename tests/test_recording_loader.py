"""
test_recording_loader — Tests for tools/recording_loader.py.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
from tools.recording_loader import load_recording


def test_load_recording_returns_source_when_found():
    source = load_recording("investor", "login")
    assert source is not None
    assert "goto" in source


def test_load_recording_returns_none_when_missing():
    assert load_recording("investor", "does_not_exist") is None
