"""File-shaped helpers the Settings dialog needs but is not made of.

Split out when F6's delay row arrived and `settings_dialog.py` stood at
199 of the 200-line ceiling (`test_ui_house_style.py:170`). Masking a key
for display and serialising a provider document are both about the FILE,
not about the widget, so this is a responsibility split rather than a
line-count dodge -- but the line count is what forced the question.
"""

from __future__ import annotations

import io

MASK = "•" * 4


def mask(key: str) -> str:
    """The loaded key, shown. Doubles as an unchanged-marker: saving the
    mask re-writes the real key untouched (`settings_dialog.py:59-63`)."""
    return MASK + key[-4:] if key else ""


def dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML

    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()
