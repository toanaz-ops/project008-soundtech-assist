import pytest

from wing_parser import WingScene
from tests.conftest import _mutated_scene


@pytest.fixture(scope="module")
def vu_scene(vu_path):
    return WingScene.load(vu_path)


def _presets(scene, rule_id):
    return [f for f in scene.advisory.run() if f.rule_id == rule_id]


def test_pc1_fires_on_a_lectern_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 60.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC1")] == ["ch.20"]

def test_pc1_accepts_110_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 110.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC1") == []

def test_pc2_fires_when_the_boundary_cut_is_missing(vu_path, tmp_path, monkeypatch):
    # Correction (task-11 brief cover note #1): ChannelData.eq is built
    # from raw key "eq", not "peq" -- build_channel.py's `build()` calls
    # `eq_models.build(entry.get("eq", {}))`. Correction #2: channel 20's
    # default eq already carries a low-mid cut (1g=-7.5 @ ~299 Hz), so
    # bands 1-4 are zeroed first to get a genuinely cut-free EQ; live
    # probe (2026-08-17) confirmed eq_has_lowmid_cut is False afterward.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        eq = ae["ch"]["20"]["eq"]
        eq["on"] = True
        for i in range(1, 5):
            eq[f"{i}g"] = 0.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC2")] == ["ch.20"]

def test_pc2_accepts_a_250_hz_cut(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        eq = ae["ch"]["20"]["eq"]
        eq["on"] = True
        eq["1g"], eq["1f"], eq["1q"] = -3.0, 250.0, 1.4
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC2") == []

def test_pc3_fires_without_a_presence_lift(vu_path, tmp_path, monkeypatch):
    # Same "eq" raw-key correction as PC2. Zeroing bands 1-4 also kills
    # channel 20's default band-4 lift (2.5 dB @ 4477 Hz, outside the
    # 2-4 kHz window anyway) so the EQ is unambiguously lift-free; live
    # probe (2026-08-17) confirmed eq_has_presence_lift is False.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        eq = ae["ch"]["20"]["eq"]
        eq["on"] = True
        for i in range(1, 5):
            eq[f"{i}g"] = 0.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC3")] == ["ch.20"]

def test_pc3_accepts_a_3k_lift(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        eq = ae["ch"]["20"]["eq"]
        eq["on"] = True
        eq["2g"], eq["2f"], eq["2q"] = 2.0, 3000.0, 1.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC3") == []

def test_pc4_fires_on_a_deep_lectern_gate(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        gate = ae["ch"]["20"]["gate"]
        gate["on"], gate["range"], gate["thr"] = True, 30, -48
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC4")] == ["ch.20"]

def test_pc4_accepts_the_documented_envelope(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        gate = ae["ch"]["20"]["gate"]
        gate["on"], gate["range"], gate["thr"] = True, 12, -48
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC4") == []

def test_pc5_fires_on_heavy_speech_compression(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        dyn = ae["ch"]["20"]["dyn"]
        dyn["on"], dyn["ratio"] = True, 8
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC5")] == ["ch.20"]

def test_pc5_accepts_three_to_one(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        dyn = ae["ch"]["20"]["dyn"]
        dyn["on"], dyn["ratio"] = True, 3
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC5") == []

def test_pc6_fires_on_a_panel_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 80.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC6")] == ["ch.20"]

def test_pc6_accepts_120_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 120.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC6") == []

def test_pc7_fires_when_the_mc_has_no_weight_advantage(vu_path, tmp_path, monkeypatch):
    # Correction (task-11 brief cover note #4): automix_group is derived
    # only from postins.mode starting with "AUTO_" (build_channel._insert).
    # The brief's fixture set `on`/`w` but not `mode`; without it,
    # automix_group stays null and PC7's `where` never matches. `mode` is
    # set explicitly here so the finding actually renders (probed
    # 2026-08-17: post_insert == Insert(on=True, slot='NONE',
    # automix_group='X', automix_weight=0.0), and PC7 fires on ch.20).
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "MC"
        ins = ae["ch"]["20"]["postins"]
        ins["on"], ins["w"], ins["mode"] = True, 0, "AUTO_X"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC7")] == ["ch.20"]

def test_pc7_accepts_plus_four(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "MC"
        ins = ae["ch"]["20"]["postins"]
        ins["on"], ins["w"], ins["mode"] = True, 4, "AUTO_X"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC7") == []

def test_pc8_fires_on_an_unmuted_qa_mic(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "Q&A 1"
        ae["ch"]["20"]["mute"] = False
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC8")] == ["ch.20"]

def test_pc8_accepts_a_muted_qa_mic(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "Q&A 1"
        ae["ch"]["20"]["mute"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC8") == []


def test_pb1_fires_on_a_non_inverted_snare_bottom(vu_path, tmp_path, monkeypatch):
    # The untouched real file already carries ch.16 "Snare Bot" (effective
    # polarity False), so PB1 fires there independent of this fixture --
    # confirmed by the real-file probe below. Channel 20's default source
    # is already effective_polarity False (source_ref grp="OFF" resolves
    # to no SourceData, so the XOR is False ^ False), so the "fire" case
    # only needs the classifier name; the raw `inv` flag is set to False
    # explicitly anyway to make the fixture self-documenting.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "SNARE BOT"
        ae["ch"]["20"]["in"]["set"]["inv"] = False
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB1")] == ["ch.16", "ch.20"]

def test_pb1_silent_when_inverted(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "SNARE BOT"
        ae["ch"]["20"]["in"]["set"]["inv"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    # ch.16 (Snare Bot) still fires on the untouched real data; only ch.20
    # is suppressed by the inversion.
    assert [f.target for f in _presets(scene, "PB1")] == ["ch.16"]

def test_pb2_fires_on_a_hihat_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    # ch.21 "Hihat" (low cut 502.4 Hz) already fires on the untouched real
    # file -- see the real-file probe test below.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "HI HAT"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 100.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB2")] == ["ch.20", "ch.21"]

def test_pb2_accepts_200_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "HI HAT"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 200.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB2")] == ["ch.21"]

def test_pb3_fires_on_a_ride_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "RIDE"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 150.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB3")] == ["ch.20"]

def test_pb3_accepts_250_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "RIDE"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 250.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PB3") == []

def test_pb4_fires_on_an_overhead_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    # ch.22 "OH" (low cut 120.0 Hz) already fires on the untouched real
    # file -- see the real-file probe test below.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "OH L"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 100.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB4")] == ["ch.20", "ch.22"]

def test_pb4_accepts_300_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "OH L"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 300.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB4")] == ["ch.22"]

def test_pb5_fires_on_a_kick_hpf_above_45_hz(vu_path, tmp_path, monkeypatch):
    # ch.13 "Kick In" (low cut 55.2 Hz) already fires on the untouched
    # real file -- see the real-file probe test below.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "KICK"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 80.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB5")] == ["ch.13", "ch.20"]

def test_pb5_accepts_30_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "KICK"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 30.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB5")] == ["ch.13"]

def test_pb5_silent_with_hpf_off(vu_path, tmp_path, monkeypatch):
    # HPF off is the documented correct state for kick/bass; the rule
    # must stay silent even at a corner that would otherwise be flagged.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "KICK"
        ae["ch"]["20"]["flt"]["lc"] = False
        ae["ch"]["20"]["flt"]["lcf"] = 80.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB5")] == ["ch.13"]

def test_pb6_fires_when_click_reaches_three_iem_mixes(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "CLICK"
        for mx in ("MX5", "MX6", "MX7"):        # IEM MC, IEM CA SI 1/2
            ae["ch"]["20"]["send"][mx]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PB6")] == ["ch.20"]

def test_pb6_accepts_two_iem_mixes(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "CLICK"
        for mx in ("MX5", "MX6"):
            ae["ch"]["20"]["send"][mx]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PB6") == []


def test_band_presets_are_off_under_a_corporate_profile(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.advisory.resolver import off_event_ids
    scene = WingScene.load(vu_path)
    shows = tmp_path / "shows"; shows.mkdir(parents=True, exist_ok=True)
    (shows / "corp.yaml").write_text("rules: []\nevent: corporate\n", encoding="utf-8")
    off = off_event_ids(scene, tmp_path, "corp")
    assert {f"PB{i}" for i in range(1, 7)} <= set(off)


def test_pb1_pb2_pb4_pb5_fire_on_the_untouched_real_file(vu_scene, monkeypatch):
    """Probed directly against `user-files/example-Vu.snap` (2026-08-17):
    unlike the corporate presets, this file has real drum-family channels,
    so four of the six band rules fire without any fixture mutation.

    - PB1: ch.16 "Snare Bot" classifies drums.snare.bottom at confidence
      0.95; raw `in.set.inv` is False and its source resolves to no
      SourceData (grp "OFF"), so effective_polarity is False. Fires.
    - PB2: ch.21 "Hihat" classifies drums.hihat; raw `flt.lc` is True,
      `flt.lcf` is 502.4 Hz, outside the 160-250 Hz window. Fires.
    - PB3: no channel in the file classifies drums.ride at all. Silent.
    - PB4: ch.22 "OH" classifies drums.overhead; raw `flt.lc` is True,
      `flt.lcf` is 120.0 Hz, below the 160 Hz floor. Fires.
    - PB5: ch.13 "Kick In" classifies drums.kick.in; raw `flt.lc` is True,
      `flt.lcf` is 55.2 Hz, above the 45 Hz ceiling. ch.14 "Kick Out"
      (32.6 Hz) and ch.25 "Bass" (`flt.lc` False) both stay under/below
      threshold and do not fire.
    - PB6: ch.23 "Click" classifies utility.click but every send on it
      reads `on: False`, so `iem_send_count` is 0. Silent.

    `test_the_sample_scene_finding_counts` in test_advisory_rules.py
    guards the same fact from the total-count side: 22 findings, with
    PB1/PB2/PB4/PB5 each contributing exactly one.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = {f.rule_id: f.target for f in vu_scene.advisory.run() if f.rule_id.startswith("PB")}
    assert found == {"PB1": "ch.16", "PB2": "ch.21", "PB4": "ch.22", "PB5": "ch.13"}
    all_ids = {f.rule_id for f in vu_scene.advisory.run()}
    assert all_ids.isdisjoint({"PB3", "PB6"})


def test_corporate_presets_are_off_under_a_band_profile(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.advisory.resolver import off_event_ids
    scene = WingScene.load(vu_path)
    shows = tmp_path / "shows"; shows.mkdir(parents=True, exist_ok=True)
    (shows / "bandshow.yaml").write_text("rules: []\nevent: band\n", encoding="utf-8")
    off = off_event_ids(scene, tmp_path, "bandshow")
    assert {f"PC{i}" for i in range(1, 9)} <= set(off)
    assert all(v == "corporate" for k, v in off.items() if k.startswith("PC"))


def test_corporate_presets_are_silent_on_the_untouched_real_file(vu_scene, monkeypatch):
    """Probed directly against `user-files/example-Vu.snap` (2026-08-17):
    no channel name in the file matches the lectern/panel/qa patterns, so
    PC1/PC2/PC3/PC4/PC6/PC8 have no classified target to evaluate at all.
    Channel 8 ("M8 MC") is the file's only `speech.mc` match and its raw
    `postins` block is `{'on': False, 'mode': 'AUTO_X', 'ins': 'NONE',
    'w': -12}` -- `mode` alone would give it a non-null `automix_group`,
    but PC7's `where` also requires `channel.post_insert.on: true`, and
    this channel's insert is off, so PC7 stays silent too (`on=False`
    short-circuits before `w` is ever read). No speech-classified channel
    in the file has `dyn.on: True` with `ratio > 4.0` either, so PC5 is
    silent by the same direct-probe method used for S1/S2 in Task 10.
    `test_the_sample_scene_finding_counts` in test_advisory_rules.py
    guards the same fact from the total-count side: 18 findings, none of
    them PC-prefixed.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = {f.rule_id for f in vu_scene.advisory.run()}
    assert found.isdisjoint({f"PC{i}" for i in range(1, 9)})
