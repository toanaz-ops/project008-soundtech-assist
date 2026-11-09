"""Provenance rules of the automix knowledge tables (wave 12, spec section 9 item 3)."""

import yaml

from wing_parser.automix import knowledge


def test_shipped_tables_have_provenance_and_known_sources():
    kb = knowledge.load()  # raises ValueError listing every violation
    for name in knowledge.TABLES:
        assert knowledge.provenance_errors(name, kb.tables[name], kb.sources) == []
    for ident, source in kb.sources.items():
        assert {"cite", "url", "kind", "accessed", "opened"} <= set(source), ident
    assert kb.warnings == ()


def test_a_number_without_src_or_eng_default_is_rejected():
    ids = {"S1": {}}
    assert knowledge.provenance_errors("t", {"a": {"hz": 100}}, ids)  # no provenance
    assert knowledge.provenance_errors("t", {"a": {"hz": 100, "src": [], "confidence": "low"}}, ids)
    assert knowledge.provenance_errors("t", {"a": {"hz": 100, "src": ["S9"], "confidence": "low"}}, ids)
    assert not knowledge.provenance_errors("t", {"a": {"hz": 100, "src": [], "confidence": "eng_default"}}, ids)
    assert not knowledge.provenance_errors("t", {"a": {"hz": [1, 2], "src": ["S1"], "confidence": "low"}}, ids)


def test_owner_override_needs_toanaz_and_a_date(tmp_path):
    entry = {"file": "eq_targets", "path": ["kinds", "drums.kick", "hpf"], "value": {"hz": 40}}
    (tmp_path / "automix.yaml").write_text(yaml.safe_dump({"overrides": [
        {**entry, "source": "ToanAZ 2026-11-20 HW-191.Q1"},
        {**entry, "value": {"hz": 50}, "source": "ToanAZ said so"},
        {**entry, "value": {"hz": 60}, "source": "someone 2026-11-20"},
    ]}), encoding="utf-8")
    kb = knowledge.load(tmp_path)
    hpf = kb.eq["kinds"]["drums.kick"]["hpf"]
    assert hpf["hz"] == 40 and hpf["src"] == ["toanaz_1"] and hpf["confidence"] == "high"
    assert "ToanAZ" in kb.sources["toanaz_1"]["cite"]
    assert len(kb.warnings) == 2 and all("ignored" in w for w in kb.warnings)
    assert knowledge.load().eq["kinds"]["drums.kick"]["hpf"]["hz"] == 35  # base tables untouched
