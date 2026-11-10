"""Per-tick rate limits for full auto (AM-18) and the stepping rule.

Discrete leaves (bool, enum, string, comp ratio) switch in one step; numeric
leaves move toward the target by at most the step for their kind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_BAND = r"(?:[1-4]|l|h)"
_EQ_GAIN = re.compile(rf"ch\.\d+\.eq\.{_BAND}g")
_FADER = re.compile(r"ch\.\d+\.fdr")
_SEND = re.compile(r"ch\.\d+\.send\.\w+\.lvl")
_THRESHOLD = re.compile(r"ch\.\d+\.(?:dyn|gate)\.thr")
_RATIO = re.compile(r"ch\.\d+\.dyn\.ratio")
_RELATIVE = re.compile(rf"(?:ch\.\d+\.(?:eq\.{_BAND}f|flt\.lcf)|fx\.\d+\.(?:lc|hc|time|pdel))")


def _plain(path: str) -> str:
    return path[len("ae_data."):] if path.startswith("ae_data.") else path


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class LiveLimits:
    tick_s: float = 2.0
    max_writes_per_tick: int = 10
    fader_step_db: float = 1.5
    eq_gain_step_db: float = 1.0
    send_step_db: float = 2.0
    threshold_step_db: float = 2.0
    other_step: float = 1.0       # gate range, comp gain, Q, decay, feed ...
    relative_step: float = 0.2    # frequencies and times: fraction of the current value
    tolerance: float = 0.25       # desk re-quantisation allowed before a leaf counts as touched
    max_failing_ticks: int = 3

    def tolerance_for(self, path: str, value) -> float:
        """Re-quantisation allowed before a leaf counts as touched: absolute,
        but at least 1% of the value for frequency/time leaves (AM-59)."""
        if _is_number(value) and _RELATIVE.fullmatch(_plain(path)):
            return max(self.tolerance, 0.01 * abs(value))
        return self.tolerance

    def next_value(self, path: str, current, target):
        """One stepped move from `current` toward `target`; None when already there."""
        if current == target:
            return None
        path = _plain(path)
        if not (_is_number(current) and _is_number(target)) or _RATIO.fullmatch(path):
            return target
        if _FADER.fullmatch(path):
            step = self.fader_step_db
        elif _EQ_GAIN.fullmatch(path):
            step = self.eq_gain_step_db
        elif _SEND.fullmatch(path):
            step = self.send_step_db
        elif _THRESHOLD.fullmatch(path):
            step = self.threshold_step_db
        elif _RELATIVE.fullmatch(path):
            step = max(abs(current) * self.relative_step, 1.0)
        else:
            step = self.other_step
        return round(current + max(-step, min(step, target - current)), 2)
