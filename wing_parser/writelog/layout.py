"""The one table layout and the one outcome glyph table, shared by the HTML
report and the Log page so the two cannot drift apart."""

from __future__ import annotations

COLUMNS: tuple[str, ...] = (
    "time", "desk", "address", "label", "finding", "file_before",
    "desk_before", "written", "readback", "outcome", "kind",
)

# outcome -> (glyph, css class)
OUTCOME_BADGE: dict[str, tuple[str, str]] = {
    "sent": ("✓", "ok"),
    "clamped": ("⚠", "warn"),
    "no_reply": ("✗", "bad"),
}
