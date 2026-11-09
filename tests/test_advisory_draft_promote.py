"""Promote a draft into principles.yaml: pure half (wave 9)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory import draft_promote as dp
from wing_parser.advisory.resolver import run

HEADER = "# header line one\n# header line two\n"
SRC_VI = "ToanAZ, ghi chú giọng nói tiếng Việt: cổng nhiễu, 2026-11-09"
GATE = """
principles:
  - id: draft.gate_on
    severity: info
    source: "{source}"
    when:
      for_each: channel
      where:
        channel.gate.on: true
    message: "Gate on channel {{channel.number}}"
"""
EXISTING = """  - id: mine.old
    severity: info
    source: "ToanAZ, 2026-01-02"
    when:
      for_each: channel
      where:
        channel.mute: true
    message: "old"
"""
NOW = datetime(2026, 11, 9, 14, 5)


def _draft(root: Path, source: str = SRC_VI, name: str = "d.yaml") -> Path:
    folder = root / "drafts"
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_text(GATE.format(source=source), encoding="utf-8")
    return path


def _principles(root: Path, body: str) -> Path:
    path = root / "principles.yaml"
    path.write_bytes((HEADER + body).encode("utf-8"))
    return path


def _ids(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [e["id"] for e in data["principles"]]


def test_empty_list_gets_entry_header_kept(tmp_path):
    target = _principles(tmp_path, "principles: []\n")
    res = dp.promote(_draft(tmp_path), tmp_path, NOW)
    assert res.ok and res.error is None
    assert res.rule_ids == ("draft.gate_on",)
    text = target.read_text(encoding="utf-8")
    assert text.startswith(HEADER)
    assert _ids(target) == ["draft.gate_on"]
    assert res.backup == tmp_path / "principles.yaml.bak"
    assert res.backup.read_text(encoding="utf-8") == HEADER + "principles: []\n"


def test_existing_entry_and_header_kept_in_order(tmp_path):
    target = _principles(tmp_path, "principles:\n" + EXISTING)
    before = target.read_text(encoding="utf-8")
    res = dp.promote(_draft(tmp_path), tmp_path, NOW)
    assert res.ok
    text = target.read_text(encoding="utf-8")
    assert text.startswith(before)
    assert _ids(target) == ["mine.old", "draft.gate_on"]
    assert res.backup.read_text(encoding="utf-8") == before


def test_missing_file_is_created(tmp_path):
    res = dp.promote(_draft(tmp_path), tmp_path, NOW)
    assert res.ok and res.backup is None
    assert _ids(tmp_path / "principles.yaml") == ["draft.gate_on"]


def test_not_promotable_changes_nothing(tmp_path):
    target = _principles(tmp_path, "principles: []\n")
    draft = _draft(tmp_path, source="ToanAZ no date")
    snap = (target.read_bytes(), target.stat().st_mtime_ns,
            draft.read_bytes(), draft.stat().st_mtime_ns)
    res = dp.promote(draft, tmp_path, NOW)
    assert not res.ok and res.error
    assert snap == (target.read_bytes(), target.stat().st_mtime_ns,
                    draft.read_bytes(), draft.stat().st_mtime_ns)
    assert not (tmp_path / "principles.yaml.bak").exists()
    assert not (tmp_path / "drafts" / "promoted").exists()


def test_unknown_layout_refused_nothing_written(tmp_path):
    target = _principles(tmp_path, "principles: []\nother_key: 1\n")
    draft = _draft(tmp_path)
    before = target.read_bytes()
    res = dp.promote(draft, tmp_path, NOW)
    assert not res.ok and "by hand" in res.error
    assert target.read_bytes() == before
    assert draft.exists()
    assert not (tmp_path / "principles.yaml.bak").exists()
    assert [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []


def test_draft_moved_to_promoted(tmp_path):
    draft = _draft(tmp_path)
    res = dp.promote(draft, tmp_path, NOW)
    expected = tmp_path / "drafts" / "promoted" / "d-20261109-1405.yaml"
    assert res.moved_to == expected and expected.is_file()
    assert not draft.exists()


def test_vietnamese_source_survives_byte_for_byte(tmp_path):
    res = dp.promote(_draft(tmp_path), tmp_path, NOW)
    assert res.ok
    raw = (tmp_path / "principles.yaml").read_bytes()
    assert SRC_VI.encode("utf-8") in raw
    data = yaml.safe_load(raw.decode("utf-8"))
    assert data["principles"][0]["source"] == SRC_VI


def test_promoted_rule_fires_on_scene(tmp_path, vu_path):
    scene = WingScene.load(vu_path)
    base = {f.rule_id for f in run(scene, tmp_path)}
    assert "draft.gate_on" not in base
    assert dp.promote(_draft(tmp_path), tmp_path, NOW).ok
    assert "draft.gate_on" in {f.rule_id for f in run(scene, tmp_path)}
