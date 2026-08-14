import sys
import types

import pytest

from wing_parser.classifier import llm


def test_unavailable_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    # Fake the SDK into sys.modules so `import anthropic` inside available()
    # would succeed if it were reached. This environment never has the real
    # package installed, so without this the test would pass whether the key
    # check or the import check fired. Faking the import present isolates
    # the missing key as the actual, independent cause of False.
    monkeypatch.setitem(sys.modules, "anthropic", types.ModuleType("anthropic"))
    assert llm.available() is False


def test_explicit_disable_switch_wins_over_a_present_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert llm.available() is False


def test_classify_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.classify("My Lap", "channels") is None


def test_classify_swallows_transport_errors(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    monkeypatch.setattr(llm, "available", lambda: True)

    def explode(*args, **kwargs):
        raise RuntimeError("network is down in the venue")

    monkeypatch.setattr(llm, "_ask", explode)
    assert llm.classify("My Lap", "channels") is None


def test_classify_maps_a_model_answer_onto_a_classification(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(
        llm, "_ask", lambda name, domain, context: ("utility.playback", 0.82)
    )

    result = llm.classify("My Lap", "channels")
    assert result is not None
    assert result.kind == "utility.playback"
    assert result.confidence == pytest.approx(0.82)
    assert result.origin == "llm"


def test_confidence_is_clamped_into_range(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ask", lambda *a: ("utility.playback", 4.0))
    assert llm.classify("My Lap", "channels").confidence == pytest.approx(1.0)

    monkeypatch.setattr(llm, "_ask", lambda *a: ("utility.playback", -1.0))
    assert llm.classify("My Lap", "channels").confidence == pytest.approx(0.0)


def test_model_is_opus_5():
    assert llm.MODEL == "claude-opus-5"
