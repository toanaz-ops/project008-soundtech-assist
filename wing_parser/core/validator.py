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
    for section, expected in EXPECTED_COUNTS.items():
        if section not in ae:
            continue
        actual = len(ae[section])
        if actual != expected:
            found.append(
                Anomaly(
                    code="count_mismatch",
                    where=f"ae_data.{section}",
                    detail=f"expected {expected} entries, found {actual}",
                )
            )
    return found


def check_required_keys(ae: dict, ce: dict) -> list[Anomaly]:
    found: list[Anomaly] = []
    for section in REQUIRED_AE:
        if section not in ae:
            found.append(
                Anomaly("missing_section", f"ae_data.{section}", "section absent")
            )
    for section in REQUIRED_CE:
        if section not in ce:
            found.append(
                Anomaly("missing_section", f"ce_data.{section}", "section absent")
            )
    return found


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
