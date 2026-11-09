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


def test_crlf_file_keeps_crlf_and_prefix(tmp_path):
    target = tmp_path / "principles.yaml"
    old = (HEADER + "principles:\n" + EXISTING).replace("\n", "\r\n").encode()
    target.write_bytes(old)
    assert dp.promote(_draft(tmp_path), tmp_path, NOW).ok
    new = target.read_bytes()
    assert new.startswith(old)
    assert b"\n" not in new.replace(b"\r\n", b"")
    assert _ids(target) == ["mine.old", "draft.gate_on"]


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


@pytest.mark.parametrize("edit", [
    ("    severity: info\n",
     "    severity: info\n    hardness: flexible\n"
     "    applies_when: {monitor_bus_cnt: 2}\n"),
    ("for_each: channel", "for_each: chanel"),
])
def test_invalid_draft_refused_principles_untouched(tmp_path, edit):
    target = _principles(tmp_path, "principles: []\n")
    draft = _draft(tmp_path)
    draft.write_text(draft.read_text(encoding="utf-8").replace(*edit),
                     encoding="utf-8")
    before = target.read_bytes()
    res = dp.promote(draft, tmp_path, NOW)
    assert not res.ok and "draft.gate_on" in res.error
    assert target.read_bytes() == before
    assert draft.exists()


def test_merged_rule_check_blocks_bad_rule(tmp_path, monkeypatch):
    from wing_parser.advisory import draft_dry_run as dd
    target = _principles(tmp_path, "principles: []\n")
    draft = _draft(tmp_path)
    before = target.read_bytes()

    def boom(path, rules):
        raise ValueError("merged check failed")
    monkeypatch.setattr(dd, "check_rules", boom)
    # load_draft also calls it, so the failure comes back as a load error
    res = dp.promote(draft, tmp_path, NOW)
    assert not res.ok and "merged check failed" in res.error
    assert target.read_bytes() == before


def test_inline_empty_keeps_comment_and_trailing_lines(tmp_path):
    target = _principles(
        tmp_path, "principles: []  # keep me\n# tail one\n# tail two\n\n")
    res = dp.promote(_draft(tmp_path), tmp_path, NOW)
    assert res.ok, res.error
    text = target.read_text(encoding="utf-8")
    assert "principles:  # keep me" in text
    assert "# tail one\n# tail two\n" in text
    assert text.startswith(HEADER)
    assert _ids(target) == ["draft.gate_on"]


def test_bom_kept_on_promote(tmp_path):
    target = tmp_path / "principles.yaml"
    target.write_bytes(b"\xef\xbb\xbf" + (HEADER + "principles: []\n").encode())
    res = dp.promote(_draft(tmp_path), tmp_path, NOW)
    assert res.ok, res.error
    raw = target.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and not raw.startswith(b"\xef\xbb\xbf\xef")
    assert _ids(target) == ["draft.gate_on"]
