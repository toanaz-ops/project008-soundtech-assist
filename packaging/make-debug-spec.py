# Regenerates packaging/wing-ui-debug.spec from wing-ui.spec.
#
# Run this after ANY change to wing-ui.spec:
#     python packaging\make-debug-spec.py
#
# The debug spec differs from the main spec in exactly two transforms:
#   name="wing-ui-debug" and console=True.
# It is generated output and stays UNTRACKED -- never hand-edit it.

from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "wing-ui.spec"
TARGET = HERE / "wing-ui-debug.spec"

TRANSFORMS = {
    'name="wing-ui"': 'name="wing-ui-debug"',
    "console=False": "console=True",
}

text = SOURCE.read_text(encoding="utf-8")
for old, new in TRANSFORMS.items():
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {old!r} in {SOURCE.name}, found {text.count(old)}")
    text = text.replace(old, new)

TARGET.write_text(text, encoding="utf-8")
print(f"wrote {TARGET}")
