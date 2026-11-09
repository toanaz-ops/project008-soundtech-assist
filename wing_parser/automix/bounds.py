"""Hard safety bounds and forbidden leaves (spec section 6).

`clamp` is applied by every stage before a value becomes a Change;
`violation` is what the invariant test uses to prove it. Paths may be
given with or without the leading "ae_data.".
"""

from __future__ import annotations

import re
from fnmatch import fnmatchcase

_BAND = r"(?:[1-4]|l|h)"
_RANGES = (
    (rf"ch\.\d+\.eq\.{_BAND}g", "eq", "gain_db"),
    (rf"ch\.\d+\.eq\.{_BAND}f", "eq", "hz"),
    (rf"ch\.\d+\.eq\.{_BAND}q", "eq", "q"),
    (r"ch\.\d+\.flt\.lcf", "hpf", "hz"),
    (r"ch\.\d+\.dyn\.thr", "comp", "thr_db"),
    (r"ch\.\d+\.dyn\.gain", "comp", "gain_db"),
    (r"ch\.\d+\.gate\.thr", "gate", "thr_db"),
    (r"ch\.\d+\.gate\.range", "gate", "range_db"),
    (r"fx\.\d+\.dcy", "reverb", "dcy"),
    (r"fx\.\d+\.pdel", "reverb", "pdel"),
    (r"fx\.\d+\.lc", "reverb", "lc"),
    (r"fx\.\d+\.hc", "reverb", "hc"),
    (r"fx\.\d+\.time", "delay", "time"),
    (r"fx\.\d+\.feed", "delay", "feed"),
)
_COMPILED = tuple((re.compile(rx), table, key) for rx, table, key in _RANGES)
_FADER = re.compile(r"ch\.\d+\.fdr")
_SEND_LVL = re.compile(r"ch\.\d+\.send\.\w+\.lvl")
_RATIO = re.compile(r"ch\.\d+\.dyn\.ratio")


def normalise(path: str) -> str:
    return path[len("ae_data."):] if path.startswith("ae_data.") else path


class Bounds:
    def __init__(self, table: dict) -> None:
        self.t = table

    def forbidden(self, path: str) -> bool:
        path = normalise(path)
        return any(fnmatchcase(path, pattern) for pattern in self.t["forbidden"])

    def _range(self, path: str):
        for rx, table, key in _COMPILED:
            if rx.fullmatch(path):
                return self.t[table][key]
        return None

    def clamp(self, path: str, value: float, lead: bool = False) -> float:
        path = normalise(path)
        rng = self._range(path)
        if rng is not None:
            return min(max(value, rng[0]), rng[1])
        if _FADER.fullmatch(path):
            fader = self.t["fader"]
            return min(max(value, fader["floor_db"]), fader["lead_max_db"] if lead else fader["max_db"])
        if _SEND_LVL.fullmatch(path):
            return min(value, self.t["send"]["max_db"])
        if _RATIO.fullmatch(path):
            return min(value, self.t["comp"]["ratio_max"])
        return value

    def violation(self, path: str, value) -> str | None:
        """Why `value` is out of bounds at `path`, or None. The fader and
        send checks use the lead ceiling because a test cannot tell which
        channel was the lead."""
        path = normalise(path)
        if self.forbidden(path):
            return "forbidden leaf"
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        rng = self._range(path)
        if rng is not None and not rng[0] <= value <= rng[1]:
            return f"{value} outside {rng}"
        if _FADER.fullmatch(path):
            fader = self.t["fader"]
            if not fader["floor_db"] <= value <= fader["lead_max_db"]:
                return f"{value} outside fader bounds"
        if _SEND_LVL.fullmatch(path) and value > self.t["send"]["max_db"]:
            return f"send level {value} above {self.t['send']['max_db']}"
        if _RATIO.fullmatch(path) and value > self.t["comp"]["ratio_max"]:
            return f"ratio {value} above {self.t['comp']['ratio_max']}"
        return None
