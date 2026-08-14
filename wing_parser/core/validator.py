"""Structural checks over a raw scene.

Collects anomalies rather than raising, so a partially malformed file
still yields useful output. Nothing here interprets a value; that is the
descriptors layer's job.
"""

from __future__ import annotations

from wing_parser.core.loader import RawScene
from wing_parser.core.models import Anomaly

EXPECTED_COUNTS: dict[str, int] = {
    "ch": 40,
    "aux": 8,
    "bus": 16,
    "main": 4,
    "mtx": 8,
    "dca": 16,
    "mgrp": 8,
}

REQUIRED_AE = ("cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca", "mgrp")
REQUIRED_CE = ("cfg", "safes")


def check_counts(ae: dict) -> list[Anomaly]:
    found: list[Anomaly] = []
    if not isinstance(ae, dict):
        return found                      # already reported by check_required_keys
    for section, expected in EXPECTED_COUNTS.items():
        if section not in ae:
            continue
        value = ae[section]
        if not isinstance(value, (dict, list)):
            found.append(
                Anomaly(
                    code="malformed_section",
                    where=f"ae_data.{section}",
                    detail=f"expected a collection, found {type(value).__name__}",
                )
            )
            continue
        actual = len(value)
        if actual != expected:
            found.append(
                Anomaly(
                    code="count_mismatch",
                    where=f"ae_data.{section}",
                    detail=f"expected {expected} entries, found {actual}",
                )
            )
    return found


def _check_block(block: object, label: str, required: tuple[str, ...]) -> list[Anomaly]:
    if not isinstance(block, dict):
        return [
            Anomaly(
                code="malformed_section",
                where=label,
                detail=f"expected an object, found {type(block).__name__}",
            )
        ]
    return [
        Anomaly("missing_section", f"{label}.{section}", "section absent")
        for section in required
        if section not in block
    ]


def check_required_keys(ae: dict, ce: dict) -> list[Anomaly]:
    return _check_block(ae, "ae_data", REQUIRED_AE) + _check_block(
        ce, "ce_data", REQUIRED_CE
    )


def validate(raw: RawScene) -> list[Anomaly]:
    found: list[Anomaly] = []
    if not raw.version.known:
        found.append(
            Anomaly(
                code="unknown_version",
                where="type",
                detail=(
                    f"{raw.version.type_id} is not a known schema; "
                    f"parsing with {raw.version.label} layout — results unverified"
                ),
            )
        )
    found.extend(check_required_keys(raw.ae, raw.ce))
    found.extend(check_counts(raw.ae))
    return found
