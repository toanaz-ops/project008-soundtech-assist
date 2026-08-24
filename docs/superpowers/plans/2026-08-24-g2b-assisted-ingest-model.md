# G2b — Assisted Ingest (Model Half) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the two model jobs to ingest — propose a column mapping from a header sample, and guess cue-sheet terms the vocabulary lacks — behind a two-adapter provider layer (Anthropic + OpenAI-compatible/DeepSeek).

**Architecture:** A restricted JSON-schema dialect with pure-python validation sits under a `Provider` protocol; two adapters implement it (`anthropic` and OpenAI SDK against configurable `base_url`). Ingest gains a sampler, a proposal checker, an interactive wizard with a `--one-shot` fast lane, and three new structured segment fields (`sound/lighting/led`). Every failure path degrades to the existing manual G2a flow.

**Tech Stack:** Python 3.14 stdlib + PyYAML + ruamel.yaml; optional extras `anthropic>=0.40` (existing), `openai>=1.50` (new); openpyxl already behind `[ingest]`.

**Spec:** `docs/superpowers/specs/2026-08-24-g2b-assisted-ingest-model-design.md`

## Global Constraints

- Offline first: no test opens a socket; no test requires an API key; `anthropic` and `openai` stay uninstalled in CI.
- Deterministic core: `core/descriptors/query/advisory/showcontext/net/ingest` never call a model directly — only through `wing_parser/classifier/provider.py`.
- Never fabricate: an unchecked model proposal is never applied; import still consumes a checked mapping.
- Degrade, don't raise: missing key, missing extra, kill switch, unreachable API → one printed line, fall back to manual G2a flow (contract of `classifier/llm.py:8–13`).
- ~200-line files, split by responsibility; UTF-8 explicit on every read-modify-write.
- Existing suite must stay green after every task: `.venv\Scripts\python.exe -m pytest` (1225 passing, 1 skipped today).

---

### Task 1: Provider protocol, schema dialect, reply validator

**Files:**
- Create: `wing_parser/classifier/provider.py`
- Test: `tests/test_provider.py`

**Interfaces:**
- Produces: `ProviderError(RuntimeError)`; `validate_reply(reply: object, schema: dict) -> list[str]` (empty list = valid); `Provider(Protocol)` with `complete_json(self, system: str, user: str, schema: dict) -> dict`; `complete_json(provider, system, user, schema) -> dict` (validates, retries once, raises `ProviderError`).

The schema dialect is deliberately tiny — flat objects of `string`/`number` only, because that is all every job in this project needs and it is what both adapters can honour natively:

```python
EXAMPLE_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind"],
}
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_provider.py
"""Unit tests for the provider protocol and the reply validator."""
import pytest

from wing_classifier_shim import *  # noqa  -- REMOVE THIS LINE, real imports below
from wing_parser.classifier.provider import (
    ProviderError,
    complete_json,
    validate_reply,
)

SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind"],
}


class FakeProvider:
    """Returns queued replies, records prompts."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append((system, user, schema))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_valid_reply_has_no_problems():
    assert validate_reply({"kind": "speech.vocal"}, SCHEMA) == []


def test_missing_required_field_is_a_problem():
    problems = validate_reply({"confidence": 0.9}, SCHEMA)
    assert problems == ["missing required field 'kind'"]


def test_wrong_type_and_extra_keys():
    problems = validate_reply({"kind": 7}, SCHEMA)
    assert any("kind" in p for p in problems)


def test_non_mapping_reply_is_one_problem():
    assert validate_reply("nope", SCHEMA) == ["reply is not a JSON object"]


def test_retry_once_then_raise():
    fake = FakeProvider([{"confidence": 0.9}, {"kind": "instrument.bass"}])
    result = complete_json(fake, "sys", "user", SCHEMA)
    assert result == {"kind": "instrument.bass"}
    assert len(fake.calls) == 2


def test_two_bad_replies_raise_provider_error():
    fake = FakeProvider([{}, {}])
    with pytest.raises(ProviderError):
        complete_json(fake, "sys", "user", SCHEMA)
    assert len(fake.calls) == 2


def test_adapter_exception_is_not_retried():
    fake = FakeProvider([ProviderError("dead uplink")])
    with pytest.raises(ProviderError):
        complete_json(fake, "sys", "user", SCHEMA)
    assert len(fake.calls) == 1
```

Delete the stray shim import line shown above before committing — the real imports are the `from wing_parser...` ones.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: wing_parser.classifier.provider`

- [ ] **Step 3: Write the implementation**

```python
# wing_parser/classifier/provider.py
"""The one doorway every model call goes through.

A Provider turns (system prompt, user prompt, schema) into a validated
JSON dict. The schema dialect is deliberately tiny -- flat objects whose
values are strings or numbers -- because that covers every judgement job
in this project and is what both adapters can honour natively: Anthropic
through `messages.parse`, OpenAI-compatible endpoints through
`response_format={"type": "json_object"}` plus our own validation.

Every failure raises ProviderError. Callers degrade on it; nothing here
returns half an answer.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """A model call failed, or its answer never matched the schema."""


def _check(value: object, spec: dict, where: str, problems: list[str]) -> None:
    expected = spec.get("type")
    if expected == "string":
        if not isinstance(value, str):
            problems.append(f"{where} must be a string, got {type(value).__name__}")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            problems.append(f"{where} must be a number, got {type(value).__name__}")
    else:  # unknown dialect member -- refused loudly, not guessed around
        problems.append(f"{where}: unsupported schema type {expected!r}")


def validate_reply(reply: object, schema: dict) -> list[str]:
    """Problems with a reply against the dialect, empty list when clean."""
    if not isinstance(reply, dict):
        return ["reply is not a JSON object"]
    problems: list[str] = []
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in reply:
            problems.append(f"missing required field {name!r}")
    for name, value in reply.items():
        if name in properties:
            _check(value, properties[name], repr(name), problems)
    return problems


@runtime_checkable
class Provider(Protocol):
    def complete_json(self, system: str, user: str, schema: dict) -> dict: ...


def complete_json(
    provider: Provider, system: str, user: str, schema: dict
) -> dict:
    """One retry on a schema-invalid reply; adapter errors are not retried."""
    for attempt in range(2):
        try:
            reply = provider.complete_json(system, user, schema)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise adapter failures
            raise ProviderError(str(exc)) from exc
        problems = validate_reply(reply, schema)
        if not problems:
            return reply
        user = f"{user}\n\nYour previous reply was rejected: {'; '.join(problems)}. Reply again."
    raise ProviderError(f"reply never matched the schema: {'; '.join(problems)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_provider.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run the whole suite, then commit**

Run: `.venv\Scripts\python.exe -m pytest`
Expected: 1225+ passed, 1 skipped

```bash
git add wing_parser/classifier/provider.py tests/test_provider.py
git commit -m "Add the provider protocol and reply validator (G2b task 1)"
```

---

### Task 2: OpenAI-compatible provider (DeepSeek's doorway)

**Files:**
- Create: `wing_parser/classifier/provider_openai.py`
- Modify: `pyproject.toml:16-19` (add `openai` extra)
- Test: `tests/test_provider_openai.py`

**Interfaces:**
- Consumes: `validate_reply`, `ProviderError` from Task 1.
- Produces: `OpenAICompatProvider(model: str, api_key_env: str, base_url: str = "")` with `complete_json(system, user, schema) -> dict`. Raises `ImportError`-derived `MissingExtra` naming `pip install -e .[llm-openai]` when the SDK is absent.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_provider_openai.py
"""Request shaping for the OpenAI-compatible adapter, tested through fakes.

No test here touches the network: the openai module is faked wholesale,
because CI does not install it (global constraint: offline first).
"""
import json
import sys
import types

import pytest

from wing_parser.classifier.provider import ProviderError
from wing_parser.classifier.provider_openai import MissingExtra, OpenAICompatProvider

SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}},
    "required": ["kind"],
}


class FakeCompletions:
    def __init__(self, payload):
        self.payload = payload
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        content = json.dumps(self.payload)
        message = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


@pytest.fixture()
def fake_sdk(monkeypatch):
    """Install a stand-in `openai` module before the adapter imports it."""
    completions = FakeCompletions({"kind": "speech.mc"})
    mod = types.ModuleType("openai")

    class FakeOpenAI:
        def __init__(self, api_key=None, base_url=None):
            self.api_key = api_key
            self.base_url = base_url
            self.chat = types.SimpleNamespace(
                completions=completions
            )

    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)
    return completions


def test_request_shape(fake_sdk, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_KEY", "k-test")
    provider = OpenAICompatProvider(
        model="deepseek-chat", api_key_env="DEEPSEEK_KEY",
        base_url="https://api.deepseek.com",
    )
    result = provider.complete_json("be terse", "name a channel", SCHEMA)
    assert result == {"kind": "speech.mc"}
    kwargs = fake_sdk.last_kwargs
    # DeepSeek's json_object mode refuses a prompt without the word json
    # and an example -- docs verified 2026-08-24 -- so both must be there.
    assert kwargs["response_format"] == {"type": "json_object"}
    assert "json" in kwargs["messages"][0]["content"].lower()
    assert '"kind"' in kwargs["messages"][0]["content"]
    assert kwargs["model"] == "deepseek-chat"


def test_invalid_json_content_raises_provider_error(fake_sdk, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_KEY", "k-test")
    fake_sdk.payload = None
    fake_sdk.__self__ if False else None  # placeholder removed below
    # Replace the returned content with something unparseable:
    provider = OpenAICompatProvider(
        model="m", api_key_env="DEEPSEEK_KEY", base_url=""
    )
    fake_sdk.create = lambda **kw: (_ for _ in ()).throw(
        AssertionError("unused")
    ) if False else types.SimpleNamespace(
        choices=[types.SimpleNamespace(
            message=types.SimpleNamespace(content="not json at all"))]
    )
    with pytest.raises(ProviderError):
        provider.complete_json("s", "u", SCHEMA)


def test_missing_sdk_raises_named_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)  # import guard trips
    provider = OpenAICompatProvider(model="m", api_key_env="NOPE_KEY")
    monkeypatch.delenv("NOPE_KEY", raising=False)
    with pytest.raises((MissingExtra, ProviderError)):
        provider.complete_json("s", "u", SCHEMA)
```

Simplify the middle test before committing: construct the provider once, point `fake_sdk.create` at a closure returning `content="not json at all"`, and drop the two dead placeholder lines — they exist only because the fixture above cannot express that shape inline.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_provider_openai.py -v`
Expected: FAIL — no module `wing_parser.classifier.provider_openai`

- [ ] **Step 3: Write the implementation**

```python
# wing_parser/classifier/provider_openai.py
"""OpenAI-compatible endpoint as a Provider -- DeepSeek's doorway.

DeepSeek documents an OpenAI-SDK-shaped API (base_url api.deepseek.com)
whose chat-completions accept response_format {"type": "json_object"}.
That mode enforces valid JSON but not a shape, so the schema rides in the
prompt as an example and `complete_json` in provider.py does the
enforcement. Docs re-checked 2026-08-24.
"""

from __future__ import annotations

import json
import os

EXTRA_HINT = (
    "talking to an OpenAI-compatible model needs the openai package, "
    "which is not installed. Install it with:  pip install -e .[llm-openai]"
)


class MissingExtra(RuntimeError):
    pass


def _example(schema: dict) -> str:
    parts = ", ".join(
        f'{name}: <{spec.get("type", "string")}>'
        for name, spec in schema.get("properties", {}).items()
    )
    return "{" + parts + "}"


class OpenAICompatProvider:
    """`base_url` is what makes this cover DeepSeek, OpenAI, or a local box."""

    def __init__(self, model: str, api_key_env: str, base_url: str = ""):
        self.model = model
        self.api_key_env = api_key_env
        self.base_url = base_url

    def _client(self):
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise ProviderErrorNamed(f"environment variable {self.api_key_env!r} is not set")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise MissingExtra(EXTRA_HINT) from exc
        kwargs = {"api_key": key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        client = self._client()
        system_prompt = (
            f"{system}\n\nReply with json exactly in this shape:\n{_example(schema)}"
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except (TypeError, ValueError) as exc:
            raise ProviderErrorNamed(f"model replied with unparseable content: {exc}") from exc


class ProviderErrorNamed(Exception):
    """Local alias kept import-light; converted by provider.complete_json."""

    # NOTE: provider.complete_json wraps arbitrary exceptions into
    # ProviderError, so this alias never escapes that call.
```

Then add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
llm-openai = ["openai>=1.50"]
```

And fix the import in the implementation: `ProviderError` should be imported from `wing_parser.classifier.provider` and used directly instead of the local alias — delete `ProviderErrorNamed` and replace both uses with `ProviderError` (add `from wing_parser.classifier.provider import ProviderError` at the top). The alias exists in the sketch only to show why the import stays lazy-safe; the committed file must use the real exception.

- [ ] **Step 4: Run tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_provider_openai.py -v`
Expected: PASS

- [ ] **Step 5: Full suite, commit**

Run: `.venv\Scripts\python.exe -m pytest`
Expected: previous count + 3 passing

```bash
git add wing_parser/classifier/provider_openai.py tests/test_provider_openai.py pyproject.toml
git commit -m "Add the OpenAI-compatible provider adapter (covers DeepSeek)"
```

---

### Task 3: Anthropic adapter, and route `llm.py` through the layer

**Files:**
- Create: `wing_parser/classifier/provider_anthropic.py`
- Modify: `wing_parser/classifier/llm.py:22,72-105`
- Test: `tests/test_provider_anthropic.py`
- Existing tests that must stay green untouched: `tests/test_classifier_llm.py`

**Interfaces:**
- Consumes: `ProviderError` (Task 1).
- Produces: `AnthropicProvider(model: str, api_key_env: str = "ANTHROPIC_API_KEY")` with `complete_json(system, user, schema) -> dict`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_provider_anthropic.py
"""AnthropicAdapter request shaping through a fake SDK (offline)."""
import sys
import types

import pytest

from wing_parser.classifier.provider_anthropic import AnthropicProvider

SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind"],
}


@pytest.fixture()
def fake_sdk(monkeypatch):
    captured = {}

    def parse(**kwargs):
        captured.update(kwargs)
        guess = types.SimpleNamespace(kind="utility.playback", confidence=0.8)
        return types.SimpleNamespace(parsed_output=guess)

    mod = types.ModuleType("anthropic")

    class FakeMessages:
        parse = staticmethod(parse)

    class FakeAnthropic:
        def __init__(self):
            self.messages = FakeMessages()

    mod.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k-test")
    return captured


def test_parse_call_carries_flat_model(fake_sdk):
    provider = AnthropicProvider(model="claude-opus-5")
    result = provider.complete_json("sys", "user", SCHEMA)
    assert result == {"kind": "utility.playback", "confidence": 0.8}
    output_format = fake_sdk["output_format"]
    fields = output_format.model_fields
    assert set(fields) == {"kind", "confidence"}
    assert fake_sdk["max_tokens"] >= 4096  # thinking headroom, per llm.py:84-91
```

- [ ] **Step 2: Verify fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_provider_anthropic.py -v`
Expected: FAIL — no module

- [ ] **Step 3: Implement**

```python
# wing_parser/classifier/provider_anthropic.py
"""Anthropic as a Provider -- the shape llm.py used inline, extracted.

The schema dialect is flat string/number fields, which maps one-to-one
onto a dynamically built pydantic model for messages.parse. max_tokens
keeps the 4096 headroom llm.py:84-91 measured: thinking counts against
it and a truncated reply dies as an exception downstream.
"""

from __future__ import annotations

import os
import types

EXTRA_HINT = (
    "talking to Claude needs the anthropic package. "
    "Install it with:  pip install -e .[llm]"
)

_TYPE_MAP = {"string": (str, ...), "number": (float, ...)}


class AnthropicProvider:
    def __init__(self, model: str, api_key_env: str = "ANTHROPIC_API_KEY"):
        self.model = model
        self.api_key_env = api_key_env

    def _parse_model(self, schema: dict):
        import pydantic

        fields = {
            name: _TYPE_MAP[spec["type"]]
            for name, spec in schema["properties"].items()
        }
        return pydantic.create_model("Reply", **fields)

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise RuntimeError(f"{self.api_key_env!r} is not set")
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(EXTRA_HINT) from exc
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.parse(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": f"{system}\n\n{user}"}],
            output_format=self._parse_model(schema),
        )
        guess = response.parsed_output
        return {
            name: getattr(guess, name) for name in schema.get("properties", {})
        }
```

Note: `types` import is unused in the final file — remove it.

Then modify `llm.py`: delete `MODEL = "claude-opus-5"` (:22), the second `import anthropic` (:74) and the whole inline `client.messages.parse` block (:81–103), replacing `_ask` with:

```python
def _ask(name: str, domain: str, context: str) -> tuple[str, float]:
    """Single API call through the provider layer. Tests replace _ask itself."""
    from wing_parser.classifier.provider import complete_json
    from wing_parser.classifier.provider_anthropic import AnthropicProvider

    schema = {
        "type": "object",
        "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
        "required": ["kind", "confidence"],
    }
    reply = complete_json(
        AnthropicProvider(model=_MODEL),
        "You are labelling a mixing-console scene file.",
        _PROMPT.format(domain_word=_DOMAIN_WORD.get(domain, "channel"),
                       name=name,
                       context=f"{context}\n" if context else ""),
        schema,
    )
    return reply["kind"], reply["confidence"]
```

with `_MODEL = "claude-opus-5"` kept as a private module constant near the top. `available()` (:60–69) keeps checking `ANTHROPIC_API_KEY` + the `anthropic` import — unchanged. If `test_classifier_llm.py` monkeypatches `_ask`, it stays green by construction; if it asserts on `MODEL`, rename those references to `_MODEL` in the same task.

- [ ] **Step 4: Run both test files plus the untouched llm tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_provider_anthropic.py tests/test_classifier_llm.py -v`
Expected: PASS (all)

- [ ] **Step 5: Full suite, commit**

```bash
git add wing_parser/classifier/provider_anthropic.py wing_parser/classifier/llm.py tests/test_provider_anthropic.py
git commit -m "Extract the Anthropic call into an adapter; route llm.py through the provider layer"
```

---

### Task 4: Provider config loading and factory

**Files:**
- Modify: `wing_parser/classifier/provider.py` (append)
- Test: `tests/test_provider_config.py`

**Interfaces:**
- Produces: `ProviderConfig` dataclass `(name: str = "anthropic", model: str = "", api_key_env: str = "", base_url: str = "")`; `DEFAULT_CONFIG`; `load_config(explicit: str | Path | None = None) -> ProviderConfig` (search order: `explicit` → `$WING_PROVIDER_CONFIG` → `./provider.yaml` → defaults); `resolve(config) -> ProviderConfig` filling per-name defaults (anthropic → model claude-opus-5, env ANTHROPIC_API_KEY; openai-compat → model deepseek-chat, env DEEPSEEK_API_KEY); `make_provider(config) -> Provider`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_provider_config.py
"""Config search order, defaults, and factory dispatch."""
from pathlib import Path

from wing_parser.classifier.provider import (
    DEFAULT_CONFIG,
    load_config,
    make_provider,
    resolve,
)
# The adapter classes live in their own modules (Tasks 2 and 3), so they
# are imported from there, never from provider.py:
from wing_parser.classifier.provider_anthropic import AnthropicProvider
from wing_parser.classifier.provider_openai import OpenAICompatProvider

def test_defaults_are_anthropic_unchanged():
    cfg = resolve(DEFAULT_CONFIG)
    assert cfg.name == "anthropic"
    assert cfg.model == "claude-opus-5"
    assert cfg.api_key_env == "ANTHROPIC_API_KEY"

def test_yaml_file_wins(tmp_path, monkeypatch):
    target = tmp_path / "provider.yaml"
    target.write_text(
        "provider: openai-compat\nmodel: deepseek-v4-flash\n"
        "base_url: https://api.deepseek.com\n", encoding="utf-8"
    )
    cfg = resolve(load_config(target))
    assert cfg.name == "openai-compat"
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.api_key_env == "DEEPSEEK_API_KEY"  # filled default

def test_env_var_points_at_file(tmp_path, monkeypatch):
    target = tmp_path / "p.yaml"
    target.write_text("provider: openai-compat\n", encoding="utf-8")
    monkeypatch.setenv("WING_PROVIDER_CONFIG", str(target))
    assert load_config(None).name == "openai-compat"

def test_no_file_anywhere_gives_default(monkeypatch, tmp_path):
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    assert load_config(None) == DEFAULT_CONFIG

def test_unknown_provider_refused(tmp_path):
    target = tmp_path / "p.yaml"
    target.write_text("provider: palm\n", encoding="utf-8")
    try:
        load_config(target)
    except ValueError as exc:
        assert "palm" in str(exc)
    else:
        raise AssertionError("unknown provider accepted")

def test_make_provider_dispatch():
    cfg = resolve(load_config(None))
    assert isinstance(make_provider(cfg), AnthropicProvider)
    cfg2 = resolve(load_config(_write_openai(tmp_path)))
    assert isinstance(make_provider(cfg2), OpenAICompatProvider)
```

(with a tiny `_write_openai(tmp_path)` helper defined in the file writing the same yaml as `test_yaml_file_wins`.)

- [ ] **Step 2: Verify fail** — `.venv\Scripts\python.exe -m pytest tests/test_provider_config.py -v` → FAIL (names missing)

- [ ] **Step 3: Append to `provider.py`**

```python
# --- appended to wing_parser/classifier/provider.py ---
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProviderConfig:
    name: str = "anthropic"
    model: str = ""
    api_key_env: str = ""
    base_url: str = ""


DEFAULT_CONFIG = ProviderConfig()

_NAME_DEFAULTS = {
    "anthropic": ProviderConfig(
        name="anthropic", model="claude-opus-5", api_key_env="ANTHROPIC_API_KEY"
    ),
    "openai-compat": ProviderConfig(
        name="openai-compat", model="deepseek-chat", api_key_env="DEEPSEEK_API_KEY"
    ),
}

ENV_VAR = "WING_PROVIDER_CONFIG"


def load_config(explicit: str | Path | None = None) -> ProviderConfig:
    """explicit beats $WING_PROVIDER_CONFIG beats ./provider.yaml beats default."""
    candidates = []
    if explicit is not None:
        candidates.append(Path(explicit))
    elif os.environ.get(ENV_VAR):
        candidates.append(Path(os.environ[ENV_VAR]))
    else:
        candidates.append(Path("provider.yaml"))
    for path in candidates:
        if path.exists():
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(doc, dict):
                raise ValueError(f"{path}: top level must be a mapping.")
            name = str(doc.get("name", doc.get("provider", DEFAULT_CONFIG.name)))
            known = set(_NAME_DEFAULTS) | {"provider", "model", "api_key_env", "base_url", "name"}
            unknown = set(doc) - known
            if name not in _NAME_DEFAULTS:
                raise ValueError(
                    f"{path}: provider {name!r} is not one of: "
                    + ", ".join(sorted(_NAME_DEFAULTS))
                )
            return ProviderConfig(
                name=name,
                model=str(doc.get("model", "")),
                api_key_env=str(doc.get("api_key_env", "")),
                base_url=str(doc.get("base_url", "")),
            )
        if explicit is not None or os.environ.get(ENV_VAR):
            break  # an explicitly named file must exist; silence would lie
    return DEFAULT_CONFIG


def resolve(config: ProviderConfig) -> ProviderConfig:
    base = _NAME_DEFAULTS[config.name]
    return replace(
        config,
        model=config.model or base.model,
        api_key_env=config.api_key_env or base.api_key_env,
    )


def make_provider(config: ProviderConfig):
    resolved = resolve(config)
    if resolved.name == "anthropic":
        from wing_parser.classifier.provider_anthropic import AnthropicProvider
        return AnthropicProvider(model=resolved.model, api_key_env=resolved.api_key_env)
    from wing_parser.classifier.provider_openai import OpenAICompatProvider
    return OpenAICompatProvider(
        model=resolved.model,
        api_key_env=resolved.api_key_env,
        base_url=resolved.base_url,
    )
```

(Task 1's provider.py does not yet import `os` — the appended block must add `import os` alongside its other new imports.)

- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_provider_config.py -v` → PASS
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/classifier/provider.py tests/test_provider_config.py
git commit -m "Add provider config loading and the adapter factory"
```

---

### Task 5: Structured technical fields through the deterministic ingest

**Files:**
- Modify: `wing_parser/showcontext/ingest/mapping.py:18` (FIELDS)
- Modify: `wing_parser/showcontext/models.py:24-29` (Segment)
- Modify: `wing_parser/showcontext/ingest/build.py:139-190` (fill fields; fold unmapped columns into prefixed comments)
- Test: extend `tests/test_ingest_build.py`, `tests/test_ingest_mapping.py`

**Interfaces:**
- Produces: `Segment(id, title, time, expects, cues, sound="", lighting="", led="")`; `mapping.FIELDS = ("id", "title", "time", "performers", "note", "sound", "lighting", "led")`. `build.build(rows, resolved, lookup, blank_rows=..., headers=None)` — the new keyword `headers: dict[str,str] | None` carries the sheet's full header row so unconsumed columns fold into comments as `[<header>] <text>`.

- [ ] **Step 1: Failing tests** (append to `tests/test_ingest_mapping.py`)

```python
def test_structured_fields_are_accepted(tmp_path):
    raw = mapping.RawMapping(source="t", sheet=None, header_row=1,
                             columns={"title": "C", "sound": "F"},
                             headers={}, path=tmp_path / "m.yaml")
    headers = {"A": "TT", "B": "Start", "C": "Noi dung", "D": "Sound", "E": "Led"}
    resolved = mapping.resolve_columns(raw, headers, last_column="E")
    assert resolved.fields["sound"] == "F"
```

(append to `tests/test_ingest_build.py`)

```python
def test_sound_column_lands_in_segment():
    rows = (_row(2, {"B": "19:00", "C": "Mo dau", "D": "Nhac don khach"}),)
    resolved = SheetMapping(source="t", fields={"title": "C", "time": "B", "sound": "D"})
    out = build.build(rows, resolved, lambda t: None,
                      headers={"B": "Start", "C": "Nội dung", "D": "Sound"})
    seg = out.segments[0].segment
    assert seg.sound == "Nhac don khach"

def test_unmapped_column_folds_into_comment_with_header_prefix():
    rows = (_row(2, {"B": "19:00", "C": "Mo dau", "E": "2 ban check-in"}),)
    resolved = SheetMapping(source="t", fields={"title": "C", "time": "B"})
    out = build.build(rows, resolved, lambda t: None,
                      headers={"B": "Start", "C": "Nội dung", "E": "CHUẨN BỊ"})
    comments = " ".join(out.segments[0].comments)
    assert "[CHUẨN BỊ]" in comments and "2 ban check-in" in comments
```

(match the helpers these test files already define for `_row`/`SheetMapping` construction — open them before writing.)

- [ ] **Step 2: Verify fail** — both files → FAIL
- [ ] **Step 3: Implement**
  - mapping.py:18 → `FIELDS: tuple[str, ...] = ("id", "title", "time", "performers", "note", "sound", "lighting", "led")`
  - models.py Segment gains `sound: str = ""`, `lighting: str = ""`, `led: str = ""` after `expects`.
  - build.py: in the row loop (:139 region), after reading note: read the three structured fields verbatim the same way (`_cell(row, mapping, "sound").strip()` etc.) and pass them to the `Segment(...)` constructor at :186. When `headers` is passed, compute `consumed = set(mapping.fields.values())` and for every header letter not in `consumed` with non-empty cell text append `f"[{headers[letter]}] {cell}"` to the notes list (:162 region). `build.build` signature grows the keyword-only `headers: dict[str, str] | None = None`; callers without it behave exactly as today.
- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_ingest_mapping.py tests/test_ingest_build.py tests/test_showcontext_loader.py -v` → PASS
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/showcontext/ingest/mapping.py wing_parser/showcontext/models.py wing_parser/showcontext/ingest/build.py tests/
git commit -m "Add sound/lighting/led structured fields and fold unmapped columns into prefixed comments"
```

---

### Task 6: Emit writes the new fields only when non-empty

**Files:**
- Modify: `wing_parser/showcontext/ingest/emit.py` (segment rendering, near :62)
- Test: extend `tests/test_ingest_emit.py`

**Interfaces:**
- Consumes: Task 5's Segment fields.
- Preserves: byte-stable output for segments with all-empty technical fields (spec §7; pinned by an existing emit test — do not weaken it).

- [ ] **Step 1: Failing test** (append to `tests/test_ingest_emit.py`)

```python
def test_technical_fields_written_only_when_present():
    # Build one BuiltSegment with sound set, one without; render both.
    # Assert 'sound:' appears once, and the empty segment's block is
    # byte-identical to the pre-G2b renderer's output for the same input.
```

Write the concrete version after opening the file's existing fixtures — mirror their construction style exactly; the assertion pair is: `rendered.count("sound:") == 1` and `rendered.split("---")[i] == baseline_block` where `baseline_block` is captured by running the old code path (fields all empty).

- [ ] **Step 2: Verify fail** — FAIL (`sound:` absent)
- [ ] **Step 3: Implement** — in the segment block builder, alongside `item["expects"]` (:62): `for field_name in ("sound", "lighting", "led"): value = getattr(built.segment, field_name); if value: item[field_name] = value`. Order fixed: sound, lighting, led, after `expects`.
- [ ] **Step 4:** emit tests + `tests/test_ingest_contract.py` → PASS (the contract test pins row counts and shapes; if it pins bytes, update its expectation only for segments carrying technical fields)
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/showcontext/ingest/emit.py tests/test_ingest_emit.py
git commit -m "Emit sound/lighting/led into the show-context file when non-empty"
```

---

### Task 7: Workbook structural sampler

**Files:**
- Create: `wing_parser/showcontext/ingest/sample.py`
- Test: `tests/test_ingest_sample.py`

**Interfaces:**
- Consumes: `sheet.read_sheet` is NOT used here (it demands a header row); this opens the workbook itself — but sheet.py owns openpyxl knowledge, so sampling reuses its `_worksheet` and `_text` via import (`from wing_parser.showcontext.ingest.sheet import _text`; promote `_worksheet` to a public `worksheet_for(book, sheet)` in sheet.py rather than importing the underscore name).
- Produces: `SheetSample(name: str, lines: tuple[str, ...])`; `sample_workbook(path, *, max_sheets: int = 6, sample_rows: int = 20) -> tuple[SheetSample, ...]`. Line format: `B4='Thời gian bắt đầu'` with values truncated to 40 chars.

- [ ] **Step 1: Failing tests**

```python
# tests/test_ingest_sample.py
"""Sampler output shape, truncation, junk-sheet tolerance."""
from pathlib import Path

import pytest

from wing_parser.showcontext.ingest.sample import sample_workbook

FIXTURE = Path("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")


def test_real_bidv_sheet_produces_lettered_lines():
    samples = sample_workbook(FIXTURE, sample_rows=8)
    bidv = [s for s in samples if "KB 8.1" in s.name]
    assert bidv, [s.name for s in samples]
    joined = "\n".join(bidv[0].lines)
    assert "A5='TT'" in joined          # header row found by letter+row
    assert "B5='Thời gian" in joined    # newline in header preserved enough


def test_row_cap_respected():
    samples = sample_workbook(FIXTURE, sample_rows=3)
    for s in samples:
        assert len(s.lines) <= 3 * 10  # 3 rows, generous cells-per-row cap


def test_long_cells_truncated(tmp_path):
    # Build a 1-cell workbook via openpyxl in tmp_path with a 100-char value;
    # assert no line exceeds 60 chars.
```

(complete the third test concretely: create `wb = openpyxl.Workbook(); ws.title='X'; ws['A1']='x'*100; wb.save(p)` inside the test, then `assert all(len(line) <= 60 for s in samples for line in s.lines)`.)

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement**

```python
# wing_parser/showcontext/ingest/sample.py
"""A workbook reduced to what a model can judge layout from.

Only the first `sample_rows` rows of up to `max_sheets` sheets are
rendered, as letter=row=text triples truncated to 40 chars. This is the
~20-line header sample the design spec promises the proposer: enough to
find a header row and name columns, not enough to leak a client's whole
running order into a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wing_parser.showcontext.ingest.sheet import worksheet_for, _text

MAX_CELL = 40


@dataclass(frozen=True)
class SheetSample:
    name: str
    lines: tuple[str, ...]


def _line(letter: str, row_number: int, value: str) -> str:
    clipped = value[:MAX_CELL]
    return f"{letter}{row_number}='{clipped}'"


def sample_workbook(path, *, max_sheets=6, sample_rows=20):
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter

    book = load_workbook(Path(path), data_only=True, read_only=True)
    try:
        samples = []
        for worksheet in book.worksheets[:max_sheets]:
            lines: list[str] = []
            for row_number, row in enumerate(worksheet.iter_rows(values_only=True), 1):
                if row_number > sample_rows:
                    break
                for index, cell in enumerate(row, start=1):
                    text = _text(cell)
                    if text:
                        lines.append(_line(get_column_letter(index), row_number, text))
            samples.append(SheetSample(name=worksheet.title, lines=tuple(lines)))
        return tuple(samples)
    finally:
        book.close()
```

Plus the small refactor in `sheet.py`: rename `_worksheet` to `worksheet_for` with a one-line backwards-compatible `_worksheet = worksheet_for` alias so existing internal callsites need no edit.

- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_ingest_sample.py tests/test_ingest_sheet.py -v` → PASS
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/showcontext/ingest/sample.py wing_parser/showcontext/ingest/sheet.py tests/test_ingest_sample.py
git commit -m "Add the workbook structural sampler for mapping proposals"
```

---

### Task 8: Proposal checker — the part that never trusts the model

**Files:**
- Create: `wing_parser/showcontext/ingest/suggest.py` (checker only; proposer lands in Task 9)
- Test: `tests/test_ingest_suggest.py`

**Interfaces:**
- Produces: `MappingProposal` frozen dataclass `(sheet: str, header_row: int, columns: dict[str, str], headers: dict[str, str], problems: tuple[str, ...])`; `check_proposal(raw: dict, xlsx_path) -> tuple[str, ...]` (empty = acceptable). Checks: sheet exists; header row readable and non-empty; every proposed column letter carries text on the header row (or sits within `last_column` for the letter escape hatch); `title` among columns.

- [ ] **Step 1: Failing tests**

```python
# tests/test_ingest_suggest.py
"""The validator checks proposals against the workbook, not the model."""
from pathlib import Path

from wing_parser.showcontext.ingest.suggest import check_proposal

VIVO = Path("tests/data/05102022_vivo_ Event Rundown.xlsx")


def good_proposal():
    return {"sheet": "Rundown", "header_row": 4,
            "columns": {"id": "B", "time": "C", "title": "F"},
            "headers": {"performers": "On stage", "note": "CHUẨN BỊ"}}


def test_good_vivo_proposal_is_clean():
    assert check_proposal(good_proposal(), VIVO) == []


def test_junk_first_sheet_named_is_caught():
    bad = good_proposal() | {"sheet": "LIST"}
    problems = check_proposal(bad, VIVO)
    assert any("LIST" in p for p in problems)


def test_wrong_header_row_caught():
    bad = good_proposal() | {"header_row": 1}
    assert check_proposal(bad, VIVO)


def test_column_past_extent_caught():
    bad = good_proposal()
    bad["columns"]["title"] = "ZZ"
    assert any("ZZ" in p for p in check_proposal(bad, VIVO))


def test_missing_title_refused():
    bad = good_proposal()
    del bad["columns"]["title"]
    assert any("title" in p for p in check_proposal(bad, VIVO))
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement**

```python
# wing_parser/showcontext/ingest/suggest.py
"""Proposing a column mapping -- and refusing to trust the proposal.

check_proposal re-reads the workbook and verifies every claim. The
proposer (Task 9) calls this between the model and the human; nothing
unchecked reaches either.
"""

from __future__ import annotations

REQUIRED_COLUMN = "title"


def check_proposal(raw: dict, xlsx_path) -> tuple[str, ...]:
    from wing_parser.showcontext.ingest import sheet as sheet_mod

    name = raw.get("sheet")
    header_row = raw.get("header_row")
    columns = raw.get("columns") or {}
    problems: list[str] = []

    if not isinstance(header_row, int) or isinstance(header_row, bool) or header_row < 1:
        return (f"header_row {header_row!r} is not a row number.",)

    try:
        read = sheet_mod.read_sheet(xlsx_path, name, header_row)
    except ValueError as exc:
        return (str(exc),)

    for field, letter in sorted(columns.items()):
        upper = str(letter).strip().upper()
        if upper not in read.headers and upper != read.last_column:
            problems.append(
                f"column {field}:{upper} has no text on the header row and is "
                f"past the sheet's extent ({read.last_column})."
            )
    if REQUIRED_COLUMN not in columns:
        problems.append(f"{REQUIRED_COLUMN!r} must be among the proposed columns.")
    return tuple(problems)
```

- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_ingest_suggest.py -v` → PASS (these are the spec §11 acceptance criteria 1–2 foundations)
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/showcontext/ingest/suggest.py tests/test_ingest_suggest.py
git commit -m "Add the mapping-proposal checker that verifies claims against the workbook"
```

---

### Task 9: The proposer — prompt, call, one repair round-trip

**Files:**
- Modify: `wing_parser/showcontext/ingest/suggest.py` (append)
- Test: extend `tests/test_ingest_suggest.py`

**Interfaces:**
- Consumes: `sample_workbook` (Task 7), `check_proposal` (Task 8), `complete_json` + `Provider` (Tasks 1–4).
- Produces: `propose_mapping(xlsx_path, provider) -> MappingProposal` — calls the model once, checks, retries once feeding the checker's complaints back, returns a `MappingProposal` carrying whatever problems remain (never raises on a bad proposal; raises `ProviderError` only when the model is unusable).

- [ ] **Step 1: Failing tests**

```python
class ScriptedProvider:
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def complete_json(self, system, user, schema):
        self.prompts.append(user)
        return self.replies.pop(0)


def test_vivo_proposal_survives_end_to_end():
    provider = ScriptedProvider([
        {"sheet": "Rundown", "header_row": 4,
         "columns": {"id": "B", "time": "C", "title": "F"},
         "headers": {"performers": "On stage", "note": "CHUẨN BỊ"}},
    ])
    proposal = propose_mapping(VIVO, provider)
    assert proposal.problems == ()
    assert proposal.columns["title"] == "F"
    assert "'Rundown'" in provider.prompts[0]      # sheet names shown
    assert "LIST" in provider.prompts[0]           # junk sheet visible too


def test_bad_then_fixed_retries_with_complaints():
    provider = ScriptedProvider([
        {"sheet": "Rundown", "header_row": 99, "columns": {"title": "F"}, "headers": {}},
        {"sheet": "Rundown", "header_row": 4,
         "columns": {"id": "B", "time": "C", "title": "F"}, "headers": {}},
    ])
    proposal = propose_mapping(VIVO, provider)
    assert proposal.problems == ()
    assert "rejected" in provider.prompts[1]       # complaints were fed back
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** (append to suggest.py)

```python
SYSTEM_PROMPT = (
    "You are proposing how to read a producer's event-running-order "
    "spreadsheet as structured rows. You see each sheet's name and its "
    "first rows rendered as LETTER+ROW='text'. Pick the sheet that is the "
    "actual rundown, find the header row, and map columns. Map id/time/"
    "title by letter; map performers/note/sound/lighting/led by exact "
    "header text. Leave a field out rather than guess wrong. Reply with "
    "json in the requested shape only."
)

PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "sheet": {"type": "string"},
        "header_row": {"type": "number"},
        "columns": {"type": "string"},   # JSON-encoded dict; see _decode
        "headers": {"type": "string"},   # dialect has no object values
    },
    "required": ["sheet", "header_row", "columns"],
}


def _decode(reply: dict) -> dict:
    """The dialect is flat, so nested dicts travel as JSON-encoded strings."""
    decoded = {
        "sheet": str(reply["sheet"]),
        "header_row": int(float(reply["header_row"])),
    }
    for key in ("columns", "headers"):
        if key in reply:
            decoded[key] = json.loads(reply[key])
    return decoded


def propose_mapping(xlsx_path, provider):
    from wing_parser.classifier.provider import complete_json
    from wing_parser.showcontext.ingest.sample import sample_workbook

    samples = sample_workbook(xlsx_path)
    rendered = "\n\n".join(
        f"SHEET {s.name!r}:\n" + "\n".join(s.lines) for s in samples
    )
    user = f"Sheets:\n{rendered}\n\nPropose the mapping."
    problems: tuple[str, ...] = ()
    reply: dict = {}
    for attempt in range(2):
        sent = user if not problems else (
            f"{user}\n\nYour previous reply was rejected: {'; '.join(problems)}"
        )
        reply = complete_json(provider, SYSTEM_PROMPT, sent, PROPOSAL_SCHEMA)
        problems = check_proposal(_decode(reply), xlsx_path)
        if not problems:
            break
    decoded = _decode(reply)
    return MappingProposal(
        sheet=decoded["sheet"],
        header_row=decoded["header_row"],
        columns=decoded.get("columns", {}),
        headers=decoded.get("headers", {}),
        problems=tuple(problems),
    )
```

(add `import json` at file top; `MappingProposal` dataclass as declared in Interfaces.)

- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_ingest_suggest.py -v` → PASS
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/showcontext/ingest/suggest.py tests/test_ingest_suggest.py
git commit -m "Add propose_mapping: model proposes, checker verifies, one complaint round-trip"
```

---

### Task 10: CLI — interactive wizard and the `--one-shot` fast lane

**Files:**
- Create: `wing_parser/showcontext/ingest/wizard.py`
- Modify: `wing_parser/cli/__main__.py:106-120` (flag), `wing_parser/cli/commands.py:260-313` (branch)
- Test: `tests/test_ingest_wizard.py`

**Interfaces:**
- Consumes: Tasks 4, 5, 9.
- Produces: `run_wizard(xlsx: str, *, input_fn, print_fn, output, force, scene, one_shot: bool, config_dir=None) -> int`. Interactive order: provider availability line → sheet → header row → core columns → people/technical fields → save `<stem>.map.yaml` beside cwd → hand off to the existing import pipeline by building `RawMapping` in memory (no re-read). `--one-shot` stops right after writing the proposed `map.yaml`, printing its path.

- [ ] **Step 1: Failing tests** (scripted inputs, fake provider; no network)

```python
# tests/test_ingest_wizard.py
"""Wizard decisions are Enter-to-accept; --one-shot writes and stops."""
from pathlib import Path

from wing_parser.showcontext.ingest.wizard import run_wizard

VIVO = "tests/data/05102022_vivo_ Event Rundown.xlsx"


class YesProvider:
    """Accepts everything the model proposes (fixture from Task 9 tests)."""
    def complete_json(self, system, user, schema):
        return {
            "sheet": "Rundown", "header_row": 4,
            "columns": '{"id": "B", "time": "C", "title": "F"}',
            "headers": '{"performers": "On stage", "note": "CHUẨN BỊ"}',
        }


def test_all_enter_accepts_proposal_and_imports(capsys, tmp_path, monkeypatch):
    answers = iter([""])  # single Enter: accept everything
    written = {}
    def fake_write(text, dest):
        written["yaml"], written["ctx"] = text, dest
        return 0
    code = run_wizard(
        VIVO, input_fn=lambda *a, **k: next(answers),
        print_fn=lambda *a, **k: None,
        output=str(tmp_path / "vivo.yaml"), force=False, scene=None,
        one_shot=False,
    )
    assert code == 0


def test_one_shot_stops_after_map(tmp_path, capsys):
    code = run_wizard(
        VIVO, input_fn=lambda *a, **k: "", print_fn=capsys_print(capsys),
        output=None, force=False, scene=None, one_shot=True,
    )

def capsys_print(capsys):
    return lambda *a, **k: print(*a, file=sys.stdout, **k) or None
```

(complete both tests concretely after opening `commands.py`'s existing import test in `tests/test_cli_showcontext.py` and mirroring how it captures stdout and asserts on the produced file; the assertions to land: `one-shot` leaves exactly the map file and no show-context file, exit code 0; interactive produces the show-context file with `expects:` populated from On-stage terms resolvable offline.)

Also add a degradation test: `DeadProvider` raising `ProviderError` → wizard prints one line containing "manual" and exits 0 after walking the manual questions (sheet name typed by hand).

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement**

```python
# wing_parser/showcontext/ingest/wizard.py
"""Interactive import: the model proposes, ToanAZ presses Enter or edits.

Every question shows a default from the proposal and accepts bare Enter.
A provider failure prints one line and falls back to asking the same
questions with no defaults -- the manual G2a flow with better manners,
never a traceback.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser.classifier.normalize import clean
from wing_parser.showcontext.ingest import build, emit, mapping, propose, sheet


def _ask(prompt: str, default: str, input_fn) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input_fn(f"{prompt}{suffix}: ").strip()
    return answer or default


def _propose_or_none(xlsx, print_fn):
    try:
        from wing_parser.classifier.provider import (
            complete_json_error_free_available, load_config, make_provider,
        )
        config = resolve(load_config(None)) if False else None  # replaced below
    ...
```

The committed file replaces that sketch with the real body, which is:

```python
def _propose_or_none(xlsx, print_fn):
    from wing_parser.classifier.provider import (
        ProviderError, load_config, make_provider,
    )
    from wing_parser.showcontext.ingest.suggest import propose_mapping
    try:
        provider = make_provider(load_config(None))
        return propose_mapping(xlsx, provider)
    except ProviderError as exc:
        print_fn(f"(no model assist: {exc} -- continuing manually)")
        return None


def run_wizard(xlsx, *, input_fn=input, print_fn=print, output=None,
               force=False, scene=None, one_shot=False):
    proposal = _propose_or_none(xlsx, print_fn)
    sheet_name = _ask("Sheet", proposal.sheet if proposal else "", input_fn)
    header_row = int(_ask("Header row", str(proposal.header_row) if proposal else "1", input_fn))
    read = sheet.read_sheet(xlsx, sheet_name or None, header_row)
    print_fn("Columns: " + ", ".join(f"{k}={v}" for k, v in sorted(read.headers.items())))
    core = {}
    for field in ("id", "time", "title"):
        default = (proposal.columns.get(field, "") if proposal else "")
        answer = _ask(f"Column letter for {field}", default, input_fn)
        if answer:
            core[field] = answer.upper()
    heads = {}
    for field in ("performers", "note", "sound", "lighting", "led"):
        default = (proposal.headers.get(field, "") if proposal else "")
        answer = _ask(f"Header text for {field}", default, input_fn)
        if answer:
            heads[field] = answer
    raw = mapping.RawMapping(
        source=f"{Path(xlsx).stem} (wizard)", sheet=sheet_name or None,
        header_row=header_row, columns=core, headers=heads,
    )
    resolved = mapping.resolve_columns(raw, read.headers, read.last_column)
    map_doc = {
        "source": raw.source, "sheet": raw.sheet, "header_row": header_row,
        "columns": core, "headers": heads,
    }
    import io
    map_text = _dump_yaml(map_doc)
    map_path = Path(f"{Path(xlsx).stem}.map.yaml")
    map_path.write_text(map_text, encoding="utf-8")
    print_fn(f"mapping saved: {map_path}")
    if one_shot:
        return 0
    return _finish(xlsx, read, resolved, output=output, force=force, scene=scene)


def _dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML
    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()


def _finish(xlsx, read, resolved, *, output, force, scene):
    # Mirrors commands.showcontext_import from vocabulary onward; kept here
    # so the wizard owns one flow instead of shelling back through argparse.
    from wing_parser.classifier import cache
    vocabulary = cache.load().get("cuesheet", {})
    result = build.build(
        read.rows, resolved, lambda term: vocabulary.get(clean(term)),
        blank_rows=read.blank_rows, headers=read.headers,
    )
    proposals = None
    if scene is not None:
        proposals = propose.for_segments(result, scene)
    text = emit.render(Path(xlsx).stem, result, proposals)
    destination = Path(output) if output else None
    if destination is None:
        print(text)
    else:
        destination.write_text(text, encoding="utf-8")
    return 0
```

In `commands.py::showcontext_import` (:260): before the `mapping.load_mapping(args.mapping)` branch, add — when `args.mapping` is absent — delegation to the wizard:

```python
if getattr(args, "mapping", None) is None and not args.no_assist:
    from wing_parser.showcontext.ingest.wizard import run_wizard
    return run_wizard(
        args.sheet, output=args.output, force=args.force, scene=args.scene,
        one_shot=bool(getattr(args, "one_shot", False)),
    )
```

and keep the existing body for `--mapping` users unchanged (backward compatible). In `__main__.py` (:106-120) add:

```python
importer.add_argument("--one-shot", action="store_true",
                      help="write the proposed map.yaml and stop")
importer.add_argument("--no-assist", action="store_true",
                      help="require --mapping; skip the wizard entirely")
importer.add_argument("--mapping", default=None,
                      help="use a hand-written mapping instead of the wizard")
```

(`--mapping` likely already exists as :110-113 — verify by opening the file; if present, only add `--one-shot` and `--no-assist`.)

- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_ingest_wizard.py tests/test_cli_showcontext.py tests/test_cli.py -v` → PASS
- [ ] **Step 5:** full suite → green; commit:

```bash
git add wing_parser/showcontext/ingest/wizard.py wing_parser/cli/__main__.py wing_parser/cli/commands.py tests/test_ingest_wizard.py
git commit -m "Wire the interactive import wizard and the --one-shot fast lane"
```

---

### Task 11: J2 — guess a missing cue-sheet term, record on explicit yes

**Files:**
- Create: `wing_parser/showcontext/ingest/guess.py`
- Modify: `wing_parser/showcontext/ingest/wizard.py` (`_finish`: collect unresolved terms, offer guesses after the file renders)
- Test: `tests/test_ingest_guess.py`

**Interfaces:**
- Consumes: `complete_json`/`Provider` (Tasks 1–4), `cache.load`/`cache.remember` (`classifier/cache.py:127-157`, reused verbatim — no new write path).
- Produces: `unresolved_terms(result) -> tuple[str, ...]` (terms the lookup callable answered None to, deduplicated, in first-seen order); `propose_term(term, context, provider) -> Classification | None`; `offer_terms(terms, result_context, *, provider_factory, input_fn, print_fn, directory=None) -> int` (count recorded).

- [ ] **Step 1: Failing tests**

```python
# tests/test_ingest_guess.py
"""Guesses land in classifier.yaml only after an explicit yes."""
import types

from wing_parser.classifier import cache
from wing_parser.showcontext.ingest.guess import (
    offer_terms, propose_term, unresolved_terms,
)

TERM_SCHEMA_RESULT = {"kind": "speech.playback", "confidence": 0.7}


class TermProvider:
    def complete_json(self, system, user, schema):
        assert "Nhạc đón khách" in user
        return TERM_SCHEMA_RESULT


def test_propose_term_returns_classification():
    got = propose_term("Nhạc đón khách", ["r2: Nhạc đón khách"], TermProvider())
    assert got.kind == "speech.playback"
    assert got.origin == "g2b-assisted"


def test_yes_records_via_cache(tmp_path):
    answers = iter(["y"])
    recorded = []
    original = cache.remember
    monkey_target = cache
    def spy(name, domain, classification, directory=None):
        recorded.append((clean := name, domain, classification))
        return original(name, domain, classification, directory=tmp_path)
    monkey_target.remember = spy
    try:
        count = offer_terms(
            ["Nhạc đón khách"], {}, provider_factory=lambda: TermProvider(),
            input_fn=lambda *a, **k: next(answers), print_fn=lambda *a, **k: None,
        )
    finally:
        monkey_target.remember = original
    assert count == 1 and recorded[0][1] == "cuesheet"


def test_no_records_nothing(tmp_path):
    answers = iter(["n"])
    count = offer_terms(
        ["Nhạc đón khách"], {}, provider_factory=lambda: TermProvider(),
        input_fn=lambda *a, **k: next(answers), print_fn=lambda *a, **k: None,
        directory=tmp_path,
    )
    assert count == 0


def test_unresolved_terms_deduped_in_order():
    seen = []
    lookup = lambda term: seen.append(term) or (None if term != "mc" else "x")
    for term in ("Nhạc đón khách", "MC", "Nhạc đón khách"):
        lookup(term)
    # unresolved_terms consumes the build result instead; tested via fake:
    fake_result = types.SimpleNamespace(segments=[
        types.SimpleNamespace(segment=types.SimpleNamespace(expects=())),
    ])
    assert unresolved_terms.__doc__  # real assertions live in wizard-level test
```

(replace the last weak test with a real one against a `build.BuildResult` constructed the way `tests/test_ingest_build.py` constructs them — asserting order `("Nhạc đón khách", "PGs")` for input rows containing both twice.)

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement**

```python
# wing_parser/showcontext/ingest/guess.py
"""Offer a kind for a term the cuesheet vocabulary lacks.

The model proposes; only an explicit y from ToanAZ writes anything, and
the write goes through cache.remember -- the same atomic, round-trip
path every other classification has ever taken -- stamped
origin 'g2b-assisted'.
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are labelling terms from Vietnamese event running orders for a "
    "live-sound tool. Given a term and its row context, name the dotted "
    "kind it behaves as on a mixing console (e.g. speech.vocal, "
    "instrument.guitar.electric, utility.playback). If genuinely "
    "unknowable, kind 'unknown', confidence 0. Do not guess to be helpful."
)

TERM_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind", "confidence"],
}


def unresolved_terms(result) -> tuple[str, ...]:
    """Terms whose lookup returned None, deduplicated, first-seen order.

    build.build reports them through BuiltSegment.comments lines shaped
    `row N: term '...'` -- parse those, do not re-run the lookups.
    """
    import re

    found: list[str] = []
    for built in result.segments:
        for comment in built.comments:
            match = re.search(r"term '(.+?)'", comment)
            if match:
                term = match.group(1)
                if term not in found:
                    found.append(term)
    return tuple(found)


def propose_term(term, context_lines, provider):
    from wing_parser.classifier.matcher import Classification
    from wing_parser.classifier.provider import complete_json

    user = f"Term: {term!r}\nContext rows:\n" + "\n".join(context_lines)
    reply = complete_json(provider, SYSTEM_PROMPT, user, TERM_SCHEMA)
    kind = str(reply["kind"]).strip().casefold()
    score = min(1.0, max(0.0, float(reply["confidence"])))
    if not kind or kind == "unknown":
        return None
    return Classification(kind=kind, confidence=score, origin="g2b-assisted")


def offer_terms(terms, context_by_term, *, provider_factory, input_fn=input,
                print_fn=print, directory=None) -> int:
    from wing_parser.classifier import cache

    recorded = 0
    for term in terms:
        try:
            guess = propose_term(term, context_by_term.get(term, []), provider_factory())
        except Exception as exc:  # noqa: BLE001 - degrade like every model path
            print_fn(f"(term guessing unavailable: {exc})")
            return recorded
        if guess is None:
            continue
        answer = input_fn(f"Record '{term}' as {guess.kind}? [y/N]: ").strip().lower()
        if answer == "y":
            cache.remember(term, "cuesheet", guess, directory=directory)
            recorded += 1
    return recorded
```

Wizard integration in `_finish`: after rendering succeeds and before returning 0 —

```python
terms = guess.unresolved_terms(result)
if terms and not one_shot:
    context_by_term = _context_for(terms, read.rows)  # term -> up to 2 row renderings
    guess.offer_terms(terms, context_by_term,
                      provider_factory=lambda: make_provider(load_config(None)))
```

- [ ] **Step 4:** `.venv\Scripts\python.exe -m pytest tests/test_ingest_guess.py tests/test_ingest_wizard.py -v` → PASS; confirm no test wrote to the real `knowledge/toanaz/classifier.yaml` (suite must not touch it — `cache.remember` is called with `directory=tmp_path` in tests, and the wizard path passes `directory=None` only in live runs)
- [ ] **Step 5:** full suite → green; `git status` must show `knowledge/` untouched; commit:

```bash
git add wing_parser/showcontext/ingest/guess.py wing_parser/showcontext/ingest/wizard.py tests/test_ingest_guess.py
git commit -m "Add J2: guess missing cue-sheet terms, record only on explicit confirmation"
```

---

### Task 12: Acceptance against the real sheets + cycle closeout

**Files:**
- Test: `tests/test_g2b_acceptance.py`
- Modify: `docs/ROADMAP.md` (§3 Done table row G2b, §4 diagram NEXT marker, §5 item 1 closed)

**Interfaces:**
- Consumes: everything above.
- Produces: the spec §11 evidence, in-repo and re-runnable.

- [ ] **Step 1: Write the acceptance tests**

```python
# tests/test_g2b_acceptance.py
"""Spec §11 success criteria, minus criterion 3's live-key path (offline).

These pin the deterministic halves of J1 against the REAL sheets ToanAZ
dropped on 2026-08-24. Model-dependent behaviour is exercised through
scripted providers; the network is never touched (global constraint).
"""
from pathlib import Path

from wing_parser.showcontext.ingest.mapping import FIELDS
from wing_parser.showcontext.ingest.suggest import check_proposal
from wing_parser.showcontext.models import Segment

VIVO = Path("tests/data/05102022_vivo_ Event Rundown.xlsx")
BIDV = Path("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")


def test_spec_criterion_1_bidv_header_row_five_accepted():
    proposal = {"sheet": "KB 8.1", "header_row": 5,
                "columns": {"id": "A", "time": "B", "title": "E"},
                "headers": {"performers": "Thực hiện"}}
    assert check_proposal(proposal, BIDV) == ()


def test_spec_criterion_2_vivo_survives_blank_column_a():
    proposal = {"sheet": "Rundown", "header_row": 4,
                "columns": {"id": "B", "time": "C", "title": "F"},
                "headers": {"performers": "On stage"}}
    assert check_proposal(proposal, VIVO) == ()


def test_segment_carries_structured_fields():
    seg = Segment(id="1", title="t", sound="nhạc", lighting="đèn", led="video")
    assert (seg.sound, seg.lighting, seg.led) == ("nhạc", "đèn", "video")


def test_fields_extended_per_spec_section_7():
    assert set(FIELDS) >= {"sound", "lighting", "led"}
```

- [ ] **Step 2: Run them, then the entire suite**

Run: `.venv\Scripts\python.exe -m pytest tests/test_g2b_acceptance.py -v` then `.venv\Scripts\python.exe -m pytest`
Expected: all PASS; total ≥ 1225 + everything this plan added, 1 skipped.

- [ ] **Step 3: One live smoke against DeepSeek (manual, needs key — not part of suite)**

With `DEEPSEEK_API_KEY` set and a `provider.yaml` pointing at DeepSeek, run once:

```
pwsh -NoProfile -Command ".\.venv\Scripts\python.exe -m wing_parser showcontext import 'tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx' --one-shot"
```

Expected: `BIDV TPHCM - KỊCH BẢN SK YEP 2025..map.yaml` appears with `header_row: 5` and `title` mapped to E. Record actual output in the completion handoff — including failure, honestly, per ROADMAP §6 precedent.

- [ ] **Step 4: Update ROADMAP.md** — move G2b into the §3 Done table with its test count, clear the NEXT arrow in the §4 Mermaid diagram, mark §5 item 1 closed (real sheets read), leave item 2 open until ToanAZ seeds terms or confirms J2 covers it.

- [ ] **Step 5: Whole-branch review, then closeout**

Per ROADMAP §7: one whole-branch review on the strongest available model before merge — reviewers may run the code; every claim about another module gets checked by opening that module. Then the `task-closeout` skill (Path C): handoff, memory, roadmap sync, commit.

```bash
git add tests/test_g2b_acceptance.py docs/ROADMAP.md
git commit -m "Pin G2b acceptance criteria against the real sheets; update roadmap"
```
