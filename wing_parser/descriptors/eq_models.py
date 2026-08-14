"""Build an Eq record from the raw eq block, dispatching on eq.mdl.

The refusal path matters as much as the success path. An EQ model with no
descriptor yields bands=None rather than borrowing another model's
layout: PULSAR stores boost/attenuate pairs, not freq/gain/Q triples, and
reading it as STD would produce plausible wrong numbers rather than an
obvious failure.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import Anomaly, Eq, EqBand
from wing_parser.descriptors import registry


def _refuse(raw_eq: dict[str, Any], model: str, on: bool, anomaly: Anomaly):
    return Eq(on=on, model=model, bands=None, raw=dict(raw_eq)), [anomaly]


def build(raw_eq: dict[str, Any]) -> tuple[Eq, list[Anomaly]]:
    model = raw_eq.get("mdl", "UNKNOWN")
    on = bool(raw_eq.get("on", False))
    spec = registry.load("eq_models")["models"].get(model)

    if spec is None:
        return _refuse(
            raw_eq, model, on,
            Anomaly(
                code="descriptor_missing",
                where=f"eq.mdl={model}",
                detail=(
                    f"no band descriptor for EQ model {model!r}; "
                    "band data left unparsed rather than guessed"
                ),
            ),
        )

    bands: list[EqBand] = []
    for band_spec in spec["bands"]:
        gain_key, freq_key, q_key = band_spec["gain"], band_spec["freq"], band_spec["q"]
        if any(key not in raw_eq for key in (gain_key, freq_key, q_key)):
            return _refuse(
                raw_eq, model, on,
                Anomaly(
                    code="eq_band_incomplete",
                    where=f"eq.mdl={model}",
                    detail=(
                        f"band {band_spec['name']!r} is missing one of "
                        f"{gain_key}/{freq_key}/{q_key}"
                    ),
                ),
            )
        shape_key = band_spec.get("shape")
        bands.append(
            EqBand(
                name=str(band_spec["name"]),
                gain=float(raw_eq[gain_key]),
                freq=float(raw_eq[freq_key]),
                q=float(raw_eq[q_key]),
                shape=raw_eq.get(shape_key) if shape_key else None,
            )
        )

    return Eq(on=on, model=model, bands=tuple(bands), raw=dict(raw_eq)), []
