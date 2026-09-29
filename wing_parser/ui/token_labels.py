"""Display names for raw tokens (severity, layer, origin, ...).

The token is the data -- combo `itemData`, model value, filter key. The
name shown for it is a UI string. `label` translates for display only and
hands an unknown token back untouched, so a new severity or layer added
in the analysis layer shows raw instead of raising.
"""

from __future__ import annotations

from wing_parser.ui import texts


def label(kind: str, token: str) -> str:
    """`kind` is the table group: severity, layer, muted, match, origin."""
    key = f"token.{kind}.{str(token).replace(', ', '_')}"
    return texts.text(key) if key in texts.TEXTS else str(token)


def all_label() -> str:
    return texts.text("token.all")


def yes_no(value: bool) -> str:
    return label("muted", "yes" if value else "no")
