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


def resolve_key(shown: str, loaded_mask: str, loaded_key: str) -> str:
    """The mask doubles as an unchanged-marker: saving it untouched
    re-writes the real key, anything the operator typed replaces it.
    Split out of `settings_dialog._current_key` to keep the dialog under
    its line ceiling (`test_ui_house_style.py:170`)."""
    return loaded_key if shown == loaded_mask else shown


def dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML

    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()
