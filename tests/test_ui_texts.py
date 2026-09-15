"""Every UI string lives in one place for future language switching."""
import ast
from pathlib import Path


def test_known_keys_resolve():
    from wing_parser.ui.texts import text

    assert text("app.title") == "wing"
    assert text("page.doctor") == "Doctor"
    assert text("page.overview") == "Overview"
    assert text("page.channels") == "Channels"
    assert text("page.routing") == "Routing"
    assert text("page.diff") == "Diff"
    assert text("page.import") == "Import"
    assert text("empty.open_hint")


def test_missing_key_is_loud():
    import pytest

    from wing_parser.ui.texts import text

    with pytest.raises(KeyError):
        text("no.such.key")


# -- the i18n rule, enforced (docs/tech-debt.md#d-24) ---------------------
#
# The wave-1 spec requires every user-facing string to come from texts.py.
# Four hardcoded ones survived the hand port, so the rule is machine-read
# now: an `ast` walk over wing_parser/ui/**/*.py that fails naming
# file:line. `ast`, not a regex, so `text("k")` and `TEXTS[k]` read as
# calls and subscripts rather than as quoted text, and an f-string is seen
# for what it is -- a literal with holes in it, which bypasses texts.py
# exactly as a plain one does.

SETTERS = {
    "setText", "setWindowTitle", "setToolTip", "setPlaceholderText",
    "addMenu", "addAction",
}
# QMessageBox's statics take (parent, title, text) -- two user-facing
# strings per call, and the pre-D-24 main_window passed both as literals.
BOX_STATICS = {"information", "warning", "critical", "question", "about"}

# The allowlist is by literal VALUE, not by file:line, so it cannot rot
# into permission for whatever moves onto that line next. Every entry
# needs a reason; a user-facing string is never one.
ALLOWED_LITERALS = {
    # A cleared label. Blanking a widget is state, not language --
    # `text("channels.detail_empty")` is the one place an empty string
    # carries meaning, and it is already a texts.py entry.
    "",
}


def _ui_sources():
    root = Path(__file__).resolve().parents[1] / "wing_parser" / "ui"
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _callee_name(call):
    """The scanned name for this call, or None when it is not scanned."""
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr in SETTERS:
        return func.attr
    if (func.attr in BOX_STATICS and isinstance(func.value, ast.Name)
            and func.value.id == "QMessageBox"):
        return f"QMessageBox.{func.attr}"
    return None


def _literal_arguments(call):
    """(value, lineno) for every quoted argument, f-strings included."""
    for argument in list(call.args) + [kw.value for kw in call.keywords]:
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            yield argument.value, argument.lineno
        elif isinstance(argument, ast.JoinedStr):
            yield "".join(
                piece.value for piece in argument.values
                if isinstance(piece, ast.Constant)
                and isinstance(piece.value, str)
            ), argument.lineno


def _offenders():
    root = Path(__file__).resolve().parents[1]
    for path in _ui_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _callee_name(node)
            if name is None:
                continue
            for value, line in _literal_arguments(node):
                if value in ALLOWED_LITERALS:
                    continue
                yield (f"{path.relative_to(root).as_posix()}:{line}: "
                       f"{name} got {value!r}")


def test_no_user_facing_literal_bypasses_texts_py():
    offenders = sorted(_offenders())
    assert offenders == [], (
        "user-facing strings must come from texts.py:\n  "
        + "\n  ".join(offenders)
    )


def test_the_scan_actually_reaches_the_pages():
    """A scan that parses nothing passes forever."""
    names = {path.name for path in _ui_sources()}
    assert {"main_window.py", "menus.py", "settings_dialog.py",
            "import_page.py"} <= names
    assert len(names) >= 20


def test_the_scan_would_catch_a_regression():
    """The detector itself, pinned -- not just its verdict today."""
    tree = ast.parse(
        'label.setText("Cannot open that file")\n'
        'box.setToolTip(f"{n} findings")\n'
        'QMessageBox.critical(self, "Cannot save", str(exc))\n'
        'menu.addAction("&Open...", self.open_file)\n'
        'label.setText(text("error.open"))\n'
        'label.setText(TEXTS["error.open"])\n'
        'label.setText("")\n'
    )
    seen = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _callee_name(node):
            seen += [v for v, _ in _literal_arguments(node)
                     if v not in ALLOWED_LITERALS]
    assert seen == ["Cannot open that file", " findings", "Cannot save",
                    "&Open..."]
