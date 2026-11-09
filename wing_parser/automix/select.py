"""Which channels automix touches, who the lead is, and where the FX buses are.

Channel kinds come from the classifier; only HIGH confidence is acted on
(AM-7), the rest becomes a Skipped row so the operator can fix the name.
The classifier has no lead/backing vocal split, so the lead is chosen here
(AM-8). FX buses are found by what is inserted on them, not by their name
(AM-13).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from wing_parser.automix.options import AutomixOptions, Skipped

# Never touched, and not worth a Skipped row: the engine has nothing to say about them.
SILENT = frozenset({
    "utility.click", "utility.talkback", "utility.timecode", "utility.spare",
    "utility.ambient", "utility.remote_caller", "utility.fx_return", "drums.pad",
})
_DIRECT = frozenset({
    "drums.tom", "drums.hihat", "drums.overhead", "drums.ride", "instrument.bass",
    "instrument.keys", "instrument.strings", "instrument.horns", "utility.playback",
    "instrument.guitar.acoustic", "instrument.guitar.electric", "speech.vocal",
})


@dataclass(frozen=True)
class Strip:
    number: int
    name: str
    raw: str  # classifier kind as is
    fam: str  # table key for dynamics / balance / fx ("vocal.backing" for non-lead vocals)
    eq_kind: str  # table key for HPF / EQ
    lead: bool = False
    bottom: bool = False  # snare bottom: HPF and fader only

    @property
    def target(self) -> str:
        return f"ch.{self.number}"


@dataclass(frozen=True)
class FxBus:
    bus: int
    slot: int
    mdl: str
    role: str


def family(kind: str) -> str | None:
    """Table key for a classifier kind; None when automix has no profile for it."""
    if kind in _DIRECT:
        return kind
    if kind.startswith("speech."):
        return "speech.mc"
    for prefix in ("drums.kick", "drums.snare"):
        if kind.startswith(prefix):
            return prefix
    if kind.startswith("instrument.guitar"):
        return "instrument.guitar.electric"
    return None


def select(scene, options: AutomixOptions) -> tuple[list[Strip], list[Skipped]]:
    strips: list[Strip] = []
    skipped: list[Skipped] = []
    for channel in scene.channels():
        number, name = channel.data.number, (channel.data.name or "").strip()
        if not name:
            continue
        guess = channel.source_type
        if guess.kind in SILENT:
            continue
        if guess.confidence < options.min_confidence:
            skipped.append(Skipped(f"ch.{number}", f"{name!r}: low classifier confidence "
                                                    f"{guess.confidence:.1f} ({guess.kind})"))
            continue
        fam = family(guess.kind)
        if fam is None:
            skipped.append(Skipped(f"ch.{number}", f"{name!r}: no automix profile for {guess.kind}"))
            continue
        strips.append(Strip(number, name, guess.kind, fam, fam,
                            bottom=guess.kind == "drums.snare.bottom"))
    return _assign_lead(strips, options), skipped


def _assign_lead(strips: list[Strip], options: AutomixOptions) -> list[Strip]:
    speech_genre = options.genre == "speech"
    pick = [s for s in strips if s.number in options.lead_channels]
    if not pick:
        pool = [s for s in strips if (s.raw.startswith("speech.") if speech_genre else s.raw == "speech.vocal")]
        pick = pool[:1]
    leads = {s.number for s in pick}
    out = []
    for s in strips:
        lead = s.number in leads
        if s.raw == "speech.vocal" and not lead and not speech_genre:
            s = Strip(s.number, s.name, s.raw, "vocal.backing", "speech.vocal", False, s.bottom)
        elif lead:
            s = Strip(s.number, s.name, s.raw, s.fam, s.eq_kind, True, s.bottom)
        out.append(s)
    return out


def fx_buses(document: dict, model_roles: dict) -> list[FxBus]:
    ae = document.get("ae_data", {})
    found: list[FxBus] = []
    for key in sorted(ae.get("bus", {}), key=int):
        for where in ("preins", "postins"):
            ins = ae["bus"][key].get(where) or {}
            match = re.fullmatch(r"FX(\d+)", str(ins.get("ins")))
            if not (ins.get("on") and match):
                continue
            mdl = (ae.get("fx", {}).get(match.group(1)) or {}).get("mdl")
            role = model_roles.get(mdl)
            item = FxBus(int(key), int(match.group(1)), str(mdl), role) if role else None
            if item and item not in found:
                found.append(item)
    return found
