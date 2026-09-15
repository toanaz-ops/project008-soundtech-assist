"""Every UI string lives in one place for future language switching.

`test_no_user_facing_literal_bypasses_texts_py` is the machine half of
that rule (docs/tech-debt.md#d-24). It is an `ast` walk, so it sees
syntax, not meaning -- and the shapes it CANNOT see are worth naming,
because a clean run is not proof the rule holds:

* **Variable-bound strings.** `FILTER = "Excel workbook (*.xlsx)"` at
  module level, handed to a scanned call as a Name. Five of the ten
  strings D-24 routed in its second pass were bound this way, and all
  five were found BY HAND during review, not by this test.
* **Strings built at runtime** -- `.format(...)`, `%`, `+` concatenation,
  `"".join(...)`, a literal that reaches a widget through a dict or a
  helper. `text("k").format(...)` is the sanctioned shape, and the scan
  cannot tell it from `"Saved {n}".format(...)`.
* **Widgets and setters outside the lists below.** Adding a Qt class or
  method to the UI does not add it here; the lists are edited by hand.

f-strings ARE caught: a literal with holes in it bypasses texts.py
exactly as a plain one does, and two such title strings were found that
way. Known residue, checked 2026-09-15 and argued rather than routed:
`__main__.py:18 MISSING_PYSIDE` (printed before Qt exists, so the
bootstrap must not depend on any import that could itself fail),
`findings_view.py:28 ALL` (a filter sentinel compared against, which
happens to be displayed), and `elide.py:23 ELLIPSIS` (typography).
Line numbers re-read from the files on 2026-09-15, after this commit's
own import shifted one of them -- a stale reference in a blind-spot
list is worse than no list, because it is read as a thing checked.

A fifth, of a different kind, added 2026-09-16 (wave 2): an
**exception's own message** shown as the line --
`live_snapshot.py:195`, `self.status_label.setText(str(exc))` for
`live_controller.EmptyReadError`. Argued on the `menus.py:82` precedent
(`QMessageBox.critical(window, text("error.open"), str(exc))`), which
this suite has accepted since wave 1: the failure's sentence is authored
where the failure is, and the frame around it -- here, none; there, a
title -- is what comes from texts.py. Invisible to the scan either way,
being a Call rather than a Constant.
"""
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
    assert text("page.console") == "Console"
    assert text("empty.open_hint")


def test_missing_key_is_loud():
    import pytest

    from wing_parser.ui.texts import text

    with pytest.raises(KeyError):
        text("no.such.key")

# -- the i18n rule, enforced (docs/tech-debt.md#d-24) ---------------------
#
# The wave-1 spec requires every user-facing string to come from texts.py.
# Four hardcoded ones survived the hand port and a first, narrower scan
# missed eight more, so both the rule and the scan's reach are pinned
# here. `ast`, not a regex, so `text("k")` and `TEXTS[k]` read as a call
# and a subscript rather than as quoted text. See this module's docstring
# for what the scan cannot see.

SETTERS = {
    "setText", "setWindowTitle", "setToolTip", "setPlaceholderText",
    "setTitle", "setTabText", "setStatusTip", "setWhatsThis",
    "addMenu", "addAction",
}
# Widget constructors take their label as the first positional argument,
# which is how "Undo the last change" and two filter-bar captions lived
# outside texts.py while the narrower scan reported zero violations.
CONSTRUCTORS = {
    "QPushButton", "QLabel", "QGroupBox", "QAction", "QMenu",
    "QCheckBox", "QRadioButton",
}
# QMessageBox's statics take (parent, title, text) -- two user-facing
# strings per call. QFileDialog's take (parent, caption, dir, filter),
# and the caption is a window title like any other.
BOX_STATICS = {"information", "warning", "critical", "question", "about"}
FILE_DIALOG_STATICS = {
    "getOpenFileName", "getSaveFileName", "getExistingDirectory",
}

# The allowlist is by literal VALUE, not by file:line, so it cannot rot
# into permission for whatever moves onto that line next. Every entry
# needs a reason; a user-facing sentence is never one.
ALLOWED_LITERALS = {
    # A cleared label. Blanking a widget is state, not language --
    # `text("channels.detail_empty")` is the one place an empty string
    # carries meaning, and it is already a texts.py entry.
    "",
    # overview_page's count cards start at zero and are overwritten by
    # the first refresh. A digit is a value, not a sentence, and it reads
    # the same in every language this file exists to enable.
    "0",
}


def _ui_sources():
    root = Path(__file__).resolve().parents[1] / "wing_parser" / "ui"
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _callee_name(call):
    """The scanned name for this call, or None when it is not scanned."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id if func.id in CONSTRUCTORS else None
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr in SETTERS or func.attr in CONSTRUCTORS:
        return func.attr
    # `QMessageBox.warning(...)` and `widgets.QMessageBox.warning(...)`
    # are the same call; match on the owner's last segment either way.
    owner = func.value
    owner_name = (
        owner.id if isinstance(owner, ast.Name)
        else owner.attr if isinstance(owner, ast.Attribute)
        else None
    )
    if owner_name == "QMessageBox" and func.attr in BOX_STATICS:
        return f"QMessageBox.{func.attr}"
    if owner_name == "QFileDialog" and func.attr in FILE_DIALOG_STATICS:
        return f"QFileDialog.{func.attr}"
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
            "import_page.py", "changes_panel.py", "findings_view.py"} <= names
    assert len(names) >= 20


def test_the_scan_would_catch_a_regression():
    """The detector itself, pinned -- not just its verdict today.

    Every widened shape is represented: a bare and an attribute-qualified
    QMessageBox static, a QFileDialog caption, a widget CONSTRUCTOR (the
    shape that let eight strings through the first scan), one of the four
    added setters, and an f-string. The sanctioned shapes -- text(),
    TEXTS[], "" and "0" -- must produce nothing.
    """
    tree = ast.parse(
        'label.setText("Cannot open that file")\n'
        'box.setToolTip(f"{n} findings")\n'
        'QMessageBox.critical(self, "Cannot save", str(exc))\n'
        'widgets.QMessageBox.warning(self, "Careful", body)\n'
        'QFileDialog.getOpenFileName(self, "Open a WING scene", "", FILTER)\n'
        'menu.addAction("&Open...", self.open_file)\n'
        'self.undo_button = QPushButton("Undo the last change")\n'
        'bar.addWidget(QtWidgets.QLabel("Severity"))\n'
        'group.setTitle("Scene counts")\n'
        'label.setText(text("error.open"))\n'
        'label.setText(TEXTS["error.open"])\n'
        'label.setText("")\n'
        'value = QLabel("0")\n'
    )
    seen = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _callee_name(node):
            seen += [v for v, _ in _literal_arguments(node)
                     if v not in ALLOWED_LITERALS]
    # Sorted: `ast.walk` is breadth-first, so a nested constructor
    # (`addWidget(QLabel("Severity"))`) surfaces after a top-level call.
    # What matters is the SET caught, not the order they were reached in.
    assert sorted(seen) == sorted([
        "Cannot open that file", " findings", "Cannot save", "Careful",
        "Open a WING scene", "&Open...", "Undo the last change", "Severity",
        "Scene counts",
    ])


def test_a_module_level_constant_is_a_known_blind_spot():
    """Named, so nobody reads a clean run as proof the rule holds.

    `FILTER = "..."` then `getOpenFileName(..., FILTER)` passes the scan:
    the argument is a Name. The four such constants D-24 routed were found
    by reading, not by this test, and the module docstring says so.
    """
    tree = ast.parse(
        'FILTER = "Excel workbook (*.xlsx)"\n'
        'QFileDialog.getOpenFileName(self, text("import.pick"), "", FILTER)\n'
    )
    seen = [v for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _callee_name(node)
            for v, _ in _literal_arguments(node) if v not in ALLOWED_LITERALS]
    assert seen == []
